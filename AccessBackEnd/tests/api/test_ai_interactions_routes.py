from app.api.v1.ai_interactions_routes import _derive_selection_from_chat


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "student"},
    )
    assert response.status_code == 201


def test_derive_selection_from_chat_returns_empty_without_chat(app):
    with app.app_context():
        provider, model_id = _derive_selection_from_chat(None)
    assert provider == ""
    assert model_id == ""


def test_derive_selection_from_chat_parses_provider_and_model(app):
    class _Chat:
        model = "huggingface::Qwen/Qwen2.5-0.5B-Instruct"

    with app.app_context():
        provider, model_id = _derive_selection_from_chat(_Chat())
    assert provider == "huggingface"
    assert model_id == "Qwen/Qwen2.5-0.5B-Instruct"


def test_publish_request_summary_includes_config_model_id(app, monkeypatch):
    from app.api.v1 import ai_interactions_routes as routes

    captured = {}

    def _capture(event_name, payload):
        captured["event_name"] = event_name
        captured["payload"] = payload

    monkeypatch.setattr(routes, "_publish", _capture)

    with app.app_context():
        app.config["AI_MODEL_NAME"] = "Qwen/Qwen2.5-0.5B-Instruct"
        routes._publish_request_summary(
            prompt="hello",
            messages=[],
            payload={},
            system_prompt=None,
            system_instructions=False,
        )

    assert captured["event_name"] == "api.ai_interaction_requested"
    assert captured["payload"]["config_model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"


def test_create_ai_interaction_uses_config_model_selection(app, client):
    from app.db import init_flask_database

    class _StubService:
        last_context = None

        def run_interaction(self, prompt, context=None, **kwargs):
            self.last_context = context or {}
            runtime = self.last_context.get("runtime_model_selection") if isinstance(self.last_context, dict) else {}
            selected_model_id = (runtime or {}).get("model_id") or "fallback"
            selected_provider = (runtime or {}).get("provider") or "huggingface"
            return {
                "assistant_text": "ok",
                "confidence": None,
                "notes": [],
                "meta": {
                    "provider": selected_provider,
                    "model_id": selected_model_id,
                    "model": selected_model_id,
                },
            }

    with app.app_context():
        init_flask_database(app)

    _register(client, "session-selection@example.com")
    app.extensions["ai_service"] = _StubService()

    with app.app_context():
        app.config["AI_PROVIDER"] = "huggingface"
        app.config["AI_MODEL_NAME"] = "Qwen/Qwen2.5-0.5B-Instruct"

    response = client.post("/api/v1/ai/interactions", json={"prompt": "hello"})
    assert response.status_code == 200

    runtime_selection = app.extensions["ai_service"].last_context["runtime_model_selection"]
    assert runtime_selection["provider"] == "huggingface"
    assert runtime_selection["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert runtime_selection["source"] == "config_default"


def test_create_ai_interaction_prefers_chat_model_selection(app, client):
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import Chat, CourseClass, DBUser

    class _StubService:
        last_context = None

        def run_interaction(self, prompt, context=None, **kwargs):
            self.last_context = context or {}
            runtime = self.last_context.get("runtime_model_selection") if isinstance(self.last_context, dict) else {}
            return {
                "assistant_text": "ok",
                "confidence": None,
                "notes": [],
                "meta": {
                    "provider": (runtime or {}).get("provider") or "huggingface",
                    "model_id": (runtime or {}).get("model_id") or "fallback",
                    "model": (runtime or {}).get("model_id") or "fallback",
                },
            }

    with app.app_context():
        init_flask_database(app)
        app.config["AI_PROVIDER"] = "huggingface"
        app.config["AI_MODEL_NAME"] = "HuggingFaceTB/SmolLM2-360M-Instruct"

    _register(client, "chat-model@example.com")
    app.extensions["ai_service"] = _StubService()

    with app.app_context():
        user = db.session.query(DBUser).filter(DBUser.email == "chat-model@example.com").one()
        class_record = CourseClass(name="Test Class", description="desc", instructor_id=int(user.id), active=True)
        db.session.add(class_record)
        db.session.flush()
        chat = Chat(
            title="chat",
            class_id=int(class_record.id),
            user_id=int(user.id),
            model="huggingface::Qwen/Qwen2.5-0.5B-Instruct",
            active=True,
        )
        db.session.add(chat)
        db.session.commit()
        chat_id = int(chat.id)

    interaction_response = client.post(
        "/api/v1/ai/interactions",
        json={"prompt": "hello", "chat_id": chat_id},
    )
    assert interaction_response.status_code == 200

    runtime_selection = app.extensions["ai_service"].last_context["runtime_model_selection"]
    assert runtime_selection["provider"] == "huggingface"
    assert runtime_selection["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert runtime_selection["source"] == "chat_model"
