from ..app.services.ai_pipeline.pipeline import (
    AIPipelineConfig,
    AIPipelineService,
)
from ..app.services.ai_pipeline.types import AIPipelineRequest


class DummyProvider:
    def __init__(self, payload=None, health_payload=None):
        self.payload = payload if payload is not None else {"assistant_text": "ok"}
        self.health_payload = health_payload if health_payload is not None else {"ok": True}
        self.calls = []

    def invoke(self, prompt, context):
        self.calls.append({"prompt": prompt, "context": context})
        return self.payload

    def health(self):
        return self.health_payload


def test_resolve_prompt_prefers_explicit_prompt():
    request = AIPipelineRequest(
        prompt="  explicit user prompt  ",
        messages=[{"role": "user", "content": "fallback"}],
    )

    assert AIPipelineService._resolve_prompt(request) == "explicit user prompt"


def test_resolve_prompt_uses_latest_user_message_when_prompt_missing():
    request = AIPipelineRequest(
        prompt=None,
        messages=[
            {"role": "assistant", "content": "ignore"},
            {"role": "user", "content": "older"},
            {"role": "user", "content": " latest user message "},
        ],
    )

    assert AIPipelineService._resolve_prompt(request) == "latest user message"


def test_run_populates_context_and_normalizes_payload():
    provider = DummyProvider(
        payload={
            "response": "model answer",
            "confidence": 0.91,
            "notes": "single note",
            "meta": {"trace": "abc123"},
        }
    )
    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="model-a", ollama_model_id="ollama-1"),
        provider=provider,
    )

    request = AIPipelineRequest(
        prompt="",
        messages=[{"role": "user", "content": "What is ADA?"}],
        system_prompt="Be concise",
        context={"chat_id": 15},
        request_id="req-7",
    )

    result = service.run(request)

    assert provider.calls[0]["prompt"] == "What is ADA?"
    sent_context = provider.calls[0]["context"]
    assert sent_context["request_id"] == "req-7"
    assert sent_context["messages"] == request.messages
    assert sent_context["system_instructions"] == "Be concise"

    assert result["assistant_text"] == "model answer"
    assert result["confidence"] == 0.91
    assert result["notes"] == ["single note"]
    assert result["meta"]["trace"] == "abc123"
    assert result["meta"]["provider"] == "ollama"
    assert result["meta"]["model"] == "ollama-1"
    assert result["meta"]["selected_provider"] == "ollama"
    assert result["meta"]["selected_model_id"] == "ollama-1"


def test_run_uses_runtime_model_selection_and_caches_provider(monkeypatch):
    created = []

    class RuntimeProvider(DummyProvider):
        def __init__(self, provider_name, model_id):
            super().__init__({"assistant_text": f"{provider_name}:{model_id}"})
            self.provider_name = provider_name
            self.model_id = model_id

    def fake_create_provider(**kwargs):
        created.append((kwargs["provider"], kwargs["model_name"]))
        return RuntimeProvider(kwargs["provider"], kwargs["model_name"])

    monkeypatch.setattr("app.services.ai_pipeline.pipeline.create_provider", fake_create_provider)

    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="default-model", ollama_model_id="default-model")
    )

    request = AIPipelineRequest(
        prompt="hello",
        context={"runtime_model_selection": {"provider": "huggingface", "model_id": "hf-1"}},
    )

    first = service.run(request)
    second = service.run(request)

    assert first["assistant_text"] == "huggingface:hf-1"
    assert second["assistant_text"] == "huggingface:hf-1"
    assert created == [("ollama", "default-model"), ("huggingface", "hf-1")]


def test_provider_health_reports_not_configured_and_health_check_failures(monkeypatch):
    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="", ollama_model_id="", huggingface_model_id="")
    )

    status = service.provider_health()
    assert status["ollama"] == {"ok": False, "status": "not_configured"}
    assert status["huggingface"] == {"ok": False, "status": "not_configured"}

    failing = AIPipelineService(
        AIPipelineConfig(provider="ollama", ollama_model_id="model-1", huggingface_model_id="hf-2")
    )

    def fail_create_provider(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(failing, "_get_or_create_provider", fail_create_provider)

    failed_status = failing.provider_health()
    assert failed_status["ollama"]["status"] == "health_check_failed"
    assert failed_status["ollama"]["model_id"] == "model-1"
    assert failed_status["huggingface"]["status"] == "health_check_failed"
    assert failed_status["huggingface"]["model_id"] == "hf-2"


def test_run_interaction_builds_request_from_prompt_and_metadata():
    provider = DummyProvider(payload={"assistant_text": "done"})
    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="m", ollama_model_id="m"),
        provider=provider,
    )

    result = service.run_interaction(
        "Need help",
        context={"system_instructions": "be brief"},
        chat_id=20,
        initiated_by="instructor",
        class_id=4,
        user_id=9,
        request_id="req-11",
    )

    assert result["assistant_text"] == "done"
    assert provider.calls[0]["prompt"] == "Need help"
    assert provider.calls[0]["context"]["system_instructions"] == "be brief"
