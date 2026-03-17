import pytest
from flask import Flask

from app.services.ai_interactions.model_resolution import AIInteractionModelResolver


class _FakeService:
    def __init__(self, inventory):
        self._inventory = inventory

    def list_available_models(self):
        return self._inventory


def test_model_resolution_returns_invalid_model_selection_when_default_unavailable():
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

    with app.test_request_context("/api/v1/ai/interactions"):
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


@pytest.mark.parametrize("inventory_key", ["local", "huggingface_local"])
def test_model_resolution_applies_config_default_when_available(inventory_key):
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
            inventory_key: {"models": [{"id": "Qwen/Qwen2.5-0.5B-Instruct"}]},
        }
    )

    with app.test_request_context("/api/v1/ai/interactions"):
        response = resolver.resolve_runtime_model_selection(
            payload,
            service,
            context_payload,
            "req-2",
        )

    assert response is None
    assert context_payload["runtime_model_selection"]["provider"] == "huggingface"
    assert context_payload["runtime_model_selection"]["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert context_payload["runtime_model_selection"]["source"] == "config_default"


def test_model_resolution_rejects_deprecated_family_override():
    resolver = AIInteractionModelResolver()
    payload = {"family_id": "qwen2_5", "provider_preference": "any"}
    context_payload = {}

    app = Flask(__name__)
    app.config.update(AI_PROVIDER="ollama", AI_MODEL_NAME="qwen2.5:0.5b", AI_OLLAMA_MODEL="qwen2.5:0.5b")

    service = _FakeService({"ollama": {"models": [{"id": "qwen2.5:0.5b"}]}, "huggingface_local": {"models": []}})

    with app.test_request_context("/api/v1/ai/interactions"):
        response, status = resolver.resolve_runtime_model_selection(payload, service, context_payload, "req-3")

    body = response.get_json()
    assert status == 400
    assert body["error"]["code"] == "invalid_model_selection"
    assert "deprecated" in body["error"]["message"].lower()
