import os
os.environ.setdefault("TEST_AI_PROVIDER", "ollama")

from app.utils import ai_checker as flow
from app.utils.ai_checker import operations as ai_ops
from flask import Flask

from app.services.ai_pipeline_v2.types import AIPipelineUpstreamError


class _FakeService:
    def list_available_models(self):
        return {
            "ollama": {"models": [{"id": "llama3.2:3b"}]},
            "huggingface_local": {"models": []},
        }


def test_resolve_model_override_uses_session_selection_when_payload_has_no_override(monkeypatch):
    payload = {"prompt": "hello"}
    context_payload = {}

    monkeypatch.setattr(
        "app.services.ai_pipeline_v2.model_selection._resolve_session_model_selection",
        lambda: {"provider": "ollama", "model_id": "llama3.2:3b"},
    )

    app = Flask(__name__)
    with app.test_request_context("/api/v1/ai/interactions"):
        flow.resolve_model_override(payload, _FakeService(), context_payload, "req-1")

    assert context_payload["runtime_model_selection"] == {
        "provider": "ollama",
        "model_id": "llama3.2:3b",
        "source": "session_selection",
    }


def test_resolve_model_override_prioritizes_request_override_over_session():
    payload = {"provider": "ollama", "model_id": "llama3.2:3b"}
    context_payload = {}

    app = Flask(__name__)
    with app.test_request_context("/api/v1/ai/interactions"):
        flow.resolve_model_override(payload, _FakeService(), context_payload, "req-2")

    assert context_payload["runtime_model_selection"]["source"] == "request_override"

def test_build_context_uses_user_feature_preferences_when_requested(monkeypatch):
    monkeypatch.setattr(
        ai_ops.AIInteractionOps,
        "_resolve_user_selected_feature_ids",
        lambda user_id: [2, 5],
    )
    monkeypatch.setattr(
        ai_ops.AIInteractionOps,
        "_resolve_system_instructions",
        lambda payload: "use selected preferences",
    )

    payload = {
        "prompt": "help",
        "use_user_feature_preferences": True,
        "selected_accessibility_link_ids": [99],
        "context": {},
    }

    app = Flask(__name__)
    with app.test_request_context('/api/v1/ai/interactions'):
        context_payload, system_instructions = flow.build_context_and_system_instructions(payload, [{"role": "user", "content": "help"}])

    assert system_instructions is not None
    assert payload["selected_accessibility_link_ids"] == [2, 5]
    assert context_payload["selected_accessibility_link_ids"] == [2, 5]
    assert context_payload["messages"][0]["content"] == "help"


class _FakeAIService:
    def __init__(self, *, model_id: str):
        self._model_id = model_id

    def list_available_models(self):
        return {
            "ollama": {"models": [{"id": "llama3.2:3b"}]},
            "huggingface_local": {"models": [{"id": self._model_id}]},
        }

    def run(self, request):
        return {
            "assistant_text": "ok",
            "meta": {
                "provider": "huggingface",
                "model_id": self._model_id,
                "model": self._model_id,
            },
        }


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "student"},
    )
    assert response.status_code == 201


def test_ai_interaction_accepts_non_numeric_model_id_without_500(app, client):
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import Chat, CourseClass, DBUser

    with app.app_context():
        init_flask_database(app)

    _register(client, "non-numeric-model@example.com")

    with app.app_context():
        user = db.session.query(DBUser).filter(DBUser.email == "non-numeric-model@example.com").one()
        class_record = CourseClass(name="Class A", description="desc", instructor_id=int(user.id), active=True)
        db.session.add(class_record)
        db.session.flush()
        chat = Chat(title="Chat A", model="hf", class_id=int(class_record.id), user_id=int(user.id))
        db.session.add(chat)
        db.session.commit()
        chat_id = int(chat.id)

    app.extensions["ai_service"] = _FakeAIService(model_id="Qwen/Qwen2.5-0.5B-Instruct")

    response = client.post(
        "/api/v1/ai/interactions",
        json={
            "prompt": "hello",
            "chat_id": chat_id,
            "messages": [{"role": "user", "content": "hello"}],
            "provider": "huggingface",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        },
    )
    assert response.status_code == 200


def test_ai_interaction_persists_valid_ai_model_fk_for_string_model_id(app, client):
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import AIInteraction, AIModel, Chat, CourseClass, DBUser

    with app.app_context():
        init_flask_database(app)

    _register(client, "fk-check-model@example.com")

    with app.app_context():
        user = db.session.query(DBUser).filter(DBUser.email == "fk-check-model@example.com").one()
        class_record = CourseClass(name="Class B", description="desc", instructor_id=int(user.id), active=True)
        db.session.add(class_record)
        db.session.flush()
        chat = Chat(title="Chat B", model="hf", class_id=int(class_record.id), user_id=int(user.id))
        db.session.add(chat)
        db.session.commit()
        chat_id = int(chat.id)

    string_model_id = "qwen2.5:0.5b"
    app.extensions["ai_service"] = _FakeAIService(model_id=string_model_id)

    response = client.post(
        "/api/v1/ai/interactions",
        json={
            "prompt": "check fk",
            "chat_id": chat_id,
            "messages": [{"role": "user", "content": "check fk"}],
            "provider": "huggingface",
            "model_id": string_model_id,
        },
    )
    assert response.status_code == 200

    with app.app_context():
        interaction = db.session.query(AIInteraction).order_by(AIInteraction.id.desc()).first()
        assert interaction is not None
        assert interaction.ai_model_id is not None

        model = db.session.get(AIModel, int(interaction.ai_model_id))
        assert model is not None
        assert int(model.id) == int(interaction.ai_model_id)
        assert model.model_id == string_model_id


def test_ai_interaction_request_model_override_beats_session_selection(app, client):
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import Chat, CourseClass, DBUser

    with app.app_context():
        init_flask_database(app)

    _register(client, "override-wins@example.com")

    with app.app_context():
        user = db.session.query(DBUser).filter(DBUser.email == "override-wins@example.com").one()
        class_record = CourseClass(name="Class C", description="desc", instructor_id=int(user.id), active=True)
        db.session.add(class_record)
        db.session.flush()
        chat = Chat(title="Chat C", model="hf", class_id=int(class_record.id), user_id=int(user.id))
        db.session.add(chat)
        db.session.commit()
        chat_id = int(chat.id)
        user_id = int(user.id)

    request_model = "Qwen/Qwen2.5-0.5B-Instruct"
    app.extensions["ai_service"] = _FakeAIService(model_id=request_model)

    with client.session_transaction() as sess:
        sess["ai_model_selection"] = {
            "user_id": user_id,
            "provider": "ollama",
            "model_id": "llama3.2:3b",
        }

    response = client.post(
        "/api/v1/ai/interactions",
        json={
            "prompt": "override check",
            "chat_id": chat_id,
            "messages": [{"role": "user", "content": "override check"}],
            "provider": "huggingface",
            "model_id": request_model,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["meta"]["selected_provider"] == "huggingface"
    assert payload["meta"]["selected_model_id"] == request_model


def test_ai_interaction_returns_provider_unavailable_error_for_failed_selected_backend(app, client):
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import Chat, CourseClass, DBUser

    class _FailingService:
        def list_available_models(self):
            return {
                "ollama": {"models": [{"id": "llama3.2:3b"}]},
                "huggingface_local": {"models": [{"id": "Qwen/Qwen2.5-0.5B-Instruct"}]},
            }

        def run(self, request):
            raise AIPipelineUpstreamError(
                "Selected provider unavailable",
                details={
                    "error_code": "provider_unavailable",
                    "provider": "huggingface",
                    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
                },
            )

    with app.app_context():
        init_flask_database(app)

    _register(client, "provider-unavailable@example.com")

    with app.app_context():
        user = db.session.query(DBUser).filter(DBUser.email == "provider-unavailable@example.com").one()
        class_record = CourseClass(name="Class D", description="desc", instructor_id=int(user.id), active=True)
        db.session.add(class_record)
        db.session.flush()
        chat = Chat(title="Chat D", model="hf", class_id=int(class_record.id), user_id=int(user.id))
        db.session.add(chat)
        db.session.commit()
        chat_id = int(chat.id)

    app.extensions["ai_service"] = _FailingService()

    response = client.post(
        "/api/v1/ai/interactions",
        json={
            "prompt": "hello",
            "chat_id": chat_id,
            "messages": [{"role": "user", "content": "hello"}],
            "provider": "huggingface",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        },
    )

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["error"]["code"] == "provider_unavailable"
