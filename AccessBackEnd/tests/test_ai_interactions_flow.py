from app.helpers import ai_interactions_flow as flow
from flask import Flask


class _FakeService:
    def list_available_models(self):
        return {
            "ollama": {"models": [{"id": "llama3.2:3b"}]},
            "huggingface_local": {"models": []},
        }


def test_resolve_model_override_uses_session_selection_when_payload_has_no_override(monkeypatch):
    monkeypatch.setattr(
        flow,
        "_resolve_session_model_selection",
        lambda: {"provider": "ollama", "model_id": "llama3.2:3b", "family_id": "llama"},
    )

    payload = {"prompt": "hello"}
    context_payload = {}

    app = Flask(__name__)
    with app.app_context():
        flow.resolve_model_override(payload, _FakeService(), context_payload, "req-1")

    assert context_payload["runtime_model_selection"] == {
        "provider": "ollama",
        "model_id": "llama3.2:3b",
        "family_id": "llama",
        "source": "session_selection",
    }


def test_resolve_model_override_prioritizes_request_override_over_session(monkeypatch):
    monkeypatch.setattr(
        flow,
        "_resolve_session_model_selection",
        lambda: {"provider": "ollama", "model_id": "llama3.2:3b", "family_id": "llama"},
    )

    payload = {"provider": "ollama", "model_id": "llama3.2:3b"}
    context_payload = {}

    app = Flask(__name__)
    with app.app_context():
        flow.resolve_model_override(payload, _FakeService(), context_payload, "req-2")

    assert context_payload["runtime_model_selection"]["source"] == "request_override"