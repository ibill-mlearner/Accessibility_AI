from flask import Flask

from ..app.services.ai_interactions.model_resolution import AIInteractionModelResolver


class _FakeService:
    def __init__(self, inventory):
        self._inventory = inventory

    def list_available_models(self):
        return self._inventory


def test_model_resolution_returns_invalid_model_selection_when_default_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_interactions.model_resolution.resolve_model_override",
        lambda payload, ai_service, context_payload, request_id: None,
    )

    resolver = AIInteractionModelResolver()
    payload = {"prompt": "hello"}
    context_payload = {}

    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER="huggingface",
        AI_MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
        AI_OLLAMA_MODEL="qwen2.5:0.5b",
    )

    service = _FakeService(
        {
            "ollama": {"models": [{"id": "qwen2.5:0.5b"}]},
            "huggingface_local": {"models": []},
        }
    )

    with app.app_context():
        response, status = resolver.resolve_runtime_model_selection(
            payload,
            service,
            context_payload,
            "req-1",
        )

    body = response.get_json()
    assert status == 400
    assert body["error"]["code"] == "invalid_model_selection"
    assert body["error"]["details"]["provider"] == "huggingface"
    assert body["error"]["details"]["available_models"] == []


def test_model_resolution_applies_config_default_when_available(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_interactions.model_resolution.resolve_model_override",
        lambda payload, ai_service, context_payload, request_id: None,
    )

    resolver = AIInteractionModelResolver()
    payload = {"prompt": "hello"}
    context_payload = {}

    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER="ollama",
        AI_MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
        AI_OLLAMA_MODEL="qwen2.5:0.5b",
    )

    service = _FakeService(
        {
            "ollama": {"models": [{"id": "qwen2.5:0.5b"}]},
            "huggingface_local": {"models": []},
        }
    )

    with app.app_context():
        response = resolver.resolve_runtime_model_selection(
            payload,
            service,
            context_payload,
            "req-2",
        )

    assert response is None
    assert context_payload["runtime_model_selection"]["provider"] == "ollama"
    assert context_payload["runtime_model_selection"]["model_id"] == "qwen2.5:0.5b"
    assert context_payload["runtime_model_selection"]["source"] == "config_default"
