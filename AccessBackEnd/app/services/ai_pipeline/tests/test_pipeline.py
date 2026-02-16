from __future__ import annotations

import io
import json

import pytest

from app.services.ai_pipeline.pipeline import AIPipelineConfig, AIPipelineService
from app.services.ai_pipeline.providers import OllamaProvider
from app.services.ai_pipeline.types import PipelineRequest


def test_run_interaction_with_mock_provider_returns_normalized_meta() -> None:
    config = AIPipelineConfig(
        provider="mock_json",
        mock_resource_path="app/resources/mock_ai_response.json",
    )
    service = AIPipelineService(config)

    payload = service.run_interaction("hello world", context={"course": "math"})

    assert isinstance(payload, dict)
    assert isinstance(payload.get("meta"), dict)
    assert payload["meta"]["provider"] == "mock_json"
    assert payload["meta"]["prompt_echo"] == "hello world"
    assert payload["meta"]["pipeline"] == "app.services.ai_pipeline"
    assert payload["meta"]["selected_provider"] == "mock_json"
    assert payload["meta"]["model"] == ""


def test_unsupported_provider_raises_value_error() -> None:
    config = AIPipelineConfig(provider="not_a_real_provider")

    with pytest.raises(ValueError, match="Unsupported AI provider"):
        AIPipelineService(config)


def test_pipeline_recovers_when_provider_returns_invalid_meta_type() -> None:
    config = AIPipelineConfig(provider="mock_json", mock_resource_path="app/resources/mock_ai_response.json")
    service = AIPipelineService(config)

    class _BadProvider:
        def invoke(self, request):  # noqa: ANN001
            return {"answer": "ok", "meta": "not-a-dict"}

    service._provider = _BadProvider()

    payload = service.run_interaction("hi")

    assert payload["answer"] == "ok"
    assert payload["meta"]["warning"] == "provider returned invalid meta payload"
    assert payload["meta"]["pipeline"] == "app.services.ai_pipeline"


def test_build_provider_uses_ollama_aliases() -> None:
    config = AIPipelineConfig(
        provider="ollama_local",
        live_endpoint="http://localhost:11434/api/generate",
        model_name="llama3:8b",
        huggingface_model_id="llama3:8b",
    )
    service = AIPipelineService(config)

    assert isinstance(service._provider, OllamaProvider)


class _FakeHTTPResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ollama_provider_parses_nested_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaProvider(
        endpoint="http://localhost:11434/api/generate",
        model_id="llama3:8b",
        timeout_seconds=1,
    )

    response_payload = {
        "model": "llama3:8b",
        "response": '{"result":"ok","confidence":0.9,"notes":["done"]}',
    }

    def _fake_urlopen(req, timeout):  # noqa: ANN001
        assert timeout == 1
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "llama3:8b"
        assert body["stream"] is False
        return _FakeHTTPResponse(json.dumps(response_payload).encode("utf-8"))

    monkeypatch.setattr("app.services.ai_pipeline.providers.urlopen", _fake_urlopen)

    payload = provider.invoke(request=PipelineRequest(prompt="hi", context={}))

    assert payload["result"] == "ok"
    assert payload["meta"]["provider"] == "ollama"
    assert payload["meta"]["model_id"] == "llama3:8b"
    assert payload["meta"]["model"] == "llama3:8b"
