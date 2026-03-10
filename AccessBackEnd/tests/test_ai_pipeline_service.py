from app.services.ai_pipeline.pipeline import (
    AIPipelineConfig,
    AIPipelineService,
)
import pytest
from app.services.ai_pipeline.exceptions import AIPipelineUpstreamError
from app.services.ai_pipeline.types import AIPipelineRequest


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


def test_run_falls_back_to_ollama_on_hf_local_only_bootstrap_error():
    class FailingHFProvider:
        model_id = "Qwen/Qwen2.5-0.5B-Instruct"

        def invoke(self, prompt, context):
            raise RuntimeError(
                "HuggingFace dynamic download is disabled in local-only mode for this POC. "
                "Provide a local model path in AI_MODEL_NAME or pre-download into AI_HUGGINGFACE_CACHE_DIR."
            )

        def health(self):
            return {"ok": False}

    class OllamaProvider:
        model_id = "qwen2.5:0.5b"

        def __init__(self):
            self.calls = []

        def invoke(self, prompt, context):
            self.calls.append({"prompt": prompt, "context": context})
            return {"assistant_text": "fallback answer"}

        def health(self):
            return {"ok": True}

    ollama = OllamaProvider()

    def provider_factory(**kwargs):
        if kwargs["provider"] == "ollama":
            return ollama
        return FailingHFProvider()

    service = AIPipelineService(
        AIPipelineConfig(
            provider="huggingface",
            model_name="Qwen/Qwen2.5-0.5B-Instruct",
            huggingface_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            huggingface_allow_download=False,
            ollama_model_id="qwen2.5:0.5b",
            ollama_endpoint="http://localhost:11434/api/chat",
            enable_ollama_fallback_on_hf_local_only_error=True,
        ),
        provider=FailingHFProvider(),
        provider_factory=provider_factory,
    )

    result = service.run(AIPipelineRequest(prompt="hello"))

    assert result["assistant_text"] == "fallback answer"
    assert result["meta"]["selected_provider"] == "ollama"
    assert result["meta"]["selected_model_id"] == "qwen2.5:0.5b"
    assert result["meta"]["fallback_from"] == "huggingface"
    assert result["meta"]["fallback_to"] == "ollama"
    assert result["meta"]["fallback_reason"] == "huggingface_local_only_bootstrap_error"
    assert ollama.calls[0]["prompt"] == "hello"


def test_run_does_not_fallback_on_non_local_only_errors():
    class FailingHFProvider:
        def invoke(self, prompt, context):
            raise RuntimeError("upstream auth failed")

        def health(self):
            return {"ok": False}

    service = AIPipelineService(
        AIPipelineConfig(
            provider="huggingface",
            model_name="Qwen/Qwen2.5-0.5B-Instruct",
            huggingface_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            huggingface_allow_download=False,
            ollama_model_id="qwen2.5:0.5b",
            ollama_endpoint="http://localhost:11434/api/chat",
        ),
        provider=FailingHFProvider(),
    )

    with pytest.raises(AIPipelineUpstreamError, match="upstream auth failed"):
        service.run(AIPipelineRequest(prompt="hello"))


def test_huggingface_prompt_assembly_includes_system_instructions(monkeypatch):
    import sys
    import types

    from app.services.ai_pipeline.providers import HuggingFaceLangChainProvider

    captured = {}

    class FakePromptTemplate:
        @classmethod
        def from_template(cls, template):
            captured["template"] = template
            return cls()

        def __or__(self, other):
            class FakeChain:
                def __or__(self, parser):
                    class FinalChain:
                        def invoke(self, payload):
                            captured["payload"] = payload
                            return '{"assistant_text":"ok"}'

                    return FinalChain()

            return FakeChain()

    class FakeHFPipeline:
        def __init__(self, pipeline):
            self.pipeline = pipeline

    class FakeParser:
        pass

    transformers_mod = types.ModuleType("transformers")
    transformers_mod.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: object())
    transformers_mod.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: object())
    transformers_mod.pipeline = lambda *args, **kwargs: object()

    langchain_llms_mod = types.ModuleType("langchain_community.llms")
    langchain_llms_mod.HuggingFacePipeline = FakeHFPipeline

    langchain_parsers_mod = types.ModuleType("langchain_core.output_parsers")
    langchain_parsers_mod.StrOutputParser = FakeParser

    langchain_prompts_mod = types.ModuleType("langchain_core.prompts")
    langchain_prompts_mod.PromptTemplate = FakePromptTemplate

    monkeypatch.setitem(sys.modules, "transformers", transformers_mod)
    monkeypatch.setitem(sys.modules, "langchain_community.llms", langchain_llms_mod)
    monkeypatch.setitem(sys.modules, "langchain_core.output_parsers", langchain_parsers_mod)
    monkeypatch.setitem(sys.modules, "langchain_core.prompts", langchain_prompts_mod)

    provider = HuggingFaceLangChainProvider(model_id="hf-test-model")
    monkeypatch.setattr(provider._bootstrap, "ensure_model", lambda: "fake-model-path")

    result = provider.invoke(
        "Explain ADA accommodations",
        {
            "system_instructions": "Prioritize accessibility-safe responses",
            "messages": [{"role": "user", "content": "hello"}],
            "chat_id": 9,
        },
    )

    assert result["assistant_text"] == "ok"
    assert "System instructions section:" in captured["template"]
    assert captured["payload"]["system_instructions"] == "Prioritize accessibility-safe responses"
    assert captured["payload"]["prompt"] == "Explain ADA accommodations"


def test_huggingface_parse_json_extracts_assistant_text_from_messages_payload():
    from app.services.ai_pipeline.providers import HuggingFaceLangChainProvider

    provider = HuggingFaceLangChainProvider(model_id="hf-test-model")
    parsed = provider._parse_json(
        '{"chat_id": 6, "messages": [{"role": "user", "content": "I want to make computer part soup"}, {"role": "assistant", "content": "Let\'s make edible soup instead."}]}'
    )

    assert parsed["assistant_text"] == "Let's make edible soup instead."
    assert "assistant_text_extracted_from_messages" in parsed["notes"]


def test_huggingface_parse_json_prefers_contract_payload_when_available():
    from app.services.ai_pipeline.providers import HuggingFaceLangChainProvider

    provider = HuggingFaceLangChainProvider(model_id="hf-test-model")
    parsed = provider._parse_json(
        '{"chat_id": 6, "assistant_text": "Use safe ingredients.", "messages": [{"role": "assistant", "content": "different"}]}'
    )

    assert parsed["assistant_text"] == "Use safe ingredients."


def test_run_falls_back_to_ollama_on_empty_huggingface_response():
    class EmptyHFProvider:
        def invoke(self, prompt, context):
            return {"assistant_text": "", "notes": ["non_json_fallback"]}

        def health(self):
            return {"ok": True}

    class OllamaProvider:
        def __init__(self):
            self.calls = []

        def invoke(self, prompt, context):
            self.calls.append({"prompt": prompt, "context": context})
            return {"assistant_text": "fallback from ollama"}

        def health(self):
            return {"ok": True}

    ollama = OllamaProvider()

    def provider_factory(**kwargs):
        if kwargs["provider"] == "ollama":
            return ollama
        return EmptyHFProvider()

    service = AIPipelineService(
        AIPipelineConfig(
            provider="huggingface",
            model_name="Qwen/Qwen2.5-0.5B-Instruct",
            huggingface_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            ollama_model_id="qwen2.5:0.5b",
            ollama_endpoint="http://localhost:11434/api/chat",
        ),
        provider=EmptyHFProvider(),
        provider_factory=provider_factory,
    )

    result = service.run(AIPipelineRequest(prompt="yes"))

    assert result["assistant_text"] == "fallback from ollama"
    assert result["meta"]["selected_provider"] == "ollama"
    assert result["meta"]["selected_model_id"] == "qwen2.5:0.5b"
    assert result["meta"]["fallback_reason"] == "huggingface_empty_response"
    assert ollama.calls[0]["prompt"] == "yes"
