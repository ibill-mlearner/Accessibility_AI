import sys
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "app" / "services")))
from ..app.services.ai_pipeline_v2.service import AIPipelineService
from ..app.services.ai_pipeline_v2.types import AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError


class DummyProvider:
    def __init__(self, payload=None, health_payload=None, models=None):
        self.payload = payload if payload is not None else {"assistant_text": "ok"}
        self.health_payload = health_payload if health_payload is not None else {"ok": True}
        self.models = models if models is not None else []
        self.calls = []

    def invoke(self, prompt, context):
        self.calls.append({"prompt": prompt, "context": context})
        return self.payload

    def health(self):
        return self.health_payload

    def inventory(self):
        return self.models

    def name(self):
        return "dummy"


def test_run_normalizes_payload_and_context():
    provider = DummyProvider(payload={"response": "answer", "confidence": 0.8, "notes": "single", "meta": {"trace": "x"}})
    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="m", ollama_model_id="m"),
        provider=provider,
    )

    result = service.run(
        AIPipelineRequest(
            prompt="",
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Be concise",
            context={"chat_id": 1},
            request_id="req-1",
        )
    )

    assert provider.calls[0]["prompt"] == "Hi"
    assert provider.calls[0]["context"]["request_id"] == "req-1"
    assert provider.calls[0]["context"]["system_instructions"] == "Be concise"
    assert result["assistant_text"] == "answer"
    assert result["notes"] == ["single"]
    assert result["meta"]["pipeline"] == "app.services.ai_pipeline_v2"


def test_runtime_selection_uses_cached_provider():
    created = []

    class RuntimeProvider(DummyProvider):
        def __init__(self, name, model):
            super().__init__({"assistant_text": f"{name}:{model}"})

    def provider_factory(config, *, provider, model_id):
        created.append((provider, model_id))
        return RuntimeProvider(provider, model_id)

    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="default", ollama_model_id="default"),
        provider_factory=provider_factory,
    )

    request = AIPipelineRequest(prompt="hello", context={"runtime_model_selection": {"provider": "huggingface", "model_id": "hf-1"}})
    first = service.run(request)
    second = service.run(request)

    assert first["assistant_text"] == "huggingface:hf-1"
    assert second["assistant_text"] == "huggingface:hf-1"
    assert created == [("huggingface", "hf-1")]


def test_hf_error_falls_back_to_ollama():
    class HF:
        def invoke(self, prompt, context):
            raise RuntimeError("HuggingFace dynamic download is disabled in local-only mode")

        def health(self):
            return {"ok": False}

        def inventory(self):
            return []

        def name(self):
            return "huggingface"

    ollama = DummyProvider({"assistant_text": "fallback"})

    def provider_factory(config, *, provider, model_id):
        if provider == "huggingface":
            return HF()
        return ollama

    service = AIPipelineService(
        AIPipelineConfig(
            provider="huggingface",
            model_name="hf-model",
            huggingface_model_id="hf-model",
            ollama_model_id="ollama-model",
            enable_ollama_fallback_on_hf_local_only_error=True,
        ),
        provider_factory=provider_factory,
    )

    result = service.run(AIPipelineRequest(prompt="help"))
    assert result["assistant_text"] == "fallback"
    assert result["meta"]["fallback_to"] == "ollama"


def test_non_fallback_error_raises_upstream_error():
    class BadProvider(DummyProvider):
        def invoke(self, prompt, context):
            raise RuntimeError("upstream auth failed")

    service = AIPipelineService(
        AIPipelineConfig(provider="huggingface", model_name="hf", huggingface_model_id="hf"),
        provider=BadProvider(),
    )

    with pytest.raises(AIPipelineUpstreamError, match="upstream auth failed"):
        service.run(AIPipelineRequest(prompt="hello"))
