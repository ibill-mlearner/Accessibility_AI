from __future__ import annotations

import json
import sys
import types

import pytest

from app.services.ai_pipeline.bootstrap import HuggingFaceModelBootstrap
from app.services.ai_pipeline.providers import (
    HTTPEndpointProvider,
    HuggingFaceLangChainProvider,
    OllamaProvider,
    _sanitize_context,
)
from app.services.ai_pipeline.types import PipelineRequest


def test_http_provider_requires_endpoint() -> None:
    provider = HTTPEndpointProvider(endpoint="")

    with pytest.raises(ValueError, match="HTTP endpoint must be configured"):
        provider.invoke(PipelineRequest(prompt="hello"))


def test_http_provider_parses_json_and_sets_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = HTTPEndpointProvider(endpoint="https://example.test/ai", model_name="gpt-4o-mini")

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return json.dumps({"result": "ok"}).encode("utf-8")

    captured = {}

    def _fake_urlopen(req, *_args, **_kwargs):  # noqa: ANN001
        captured["request_body"] = json.loads(req.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr("app.services.ai_pipeline.providers.urlopen", _fake_urlopen)

    payload = provider.invoke(PipelineRequest(prompt="hello", context={"level": 1}))

    assert captured["request_body"]["model"] == "gpt-4o-mini"
    assert payload["result"] == "ok"
    assert payload["meta"]["provider"] == "http"
    assert payload["meta"]["model"] == "gpt-4o-mini"


def test_huggingface_provider_parse_json_handles_embedded_object() -> None:
    provider = HuggingFaceLangChainProvider(model_id="demo/model")

    parsed = provider._parse_json("prefix text {\"result\": \"ok\", \"confidence\": 0.9, \"notes\": []} suffix")

    assert parsed["result"] == "ok"
    assert parsed["confidence"] == 0.9


def test_huggingface_provider_parse_json_handles_prose_plus_json_code_block() -> None:
    provider = HuggingFaceLangChainProvider(model_id="demo/model")

    parsed = provider._parse_json(
        """
        Here's your answer.
        ```json
        {"assistant_text": "Structured response", "confidence": 0.8, "notes": []}
        ```
        Thanks!
        """
    )

    assert parsed["assistant_text"] == "Structured response"
    assert parsed["confidence"] == 0.8


def test_huggingface_provider_parse_json_raises_on_invalid_json() -> None:
    provider = HuggingFaceLangChainProvider(model_id="demo/model")

    with pytest.raises(ValueError, match="not valid JSON"):
        provider._parse_json("this is not json")


def test_huggingface_provider_invoke_returns_non_json_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = HuggingFaceLangChainProvider(model_id="demo/model")
    monkeypatch.setattr(provider._bootstrap, "ensure_model", lambda: "/tmp/model")

    class _FakeChain:
        def __or__(self, _other):  # noqa: ANN001
            return self

        def invoke(self, _input):  # noqa: ANN001
            return "plain text response"

    class _FakePromptTemplate:
        @staticmethod
        def from_template(_template: str) -> _FakeChain:
            return _FakeChain()

    fake_transformers = types.SimpleNamespace(
        AutoModelForCausalLM=types.SimpleNamespace(from_pretrained=lambda *_args, **_kwargs: object()),
        AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *_args, **_kwargs: object()),
        pipeline=lambda *_args, **_kwargs: object(),
    )
    fake_langchain_llms = types.SimpleNamespace(HuggingFacePipeline=lambda **_kwargs: object())
    fake_langchain_prompts = types.SimpleNamespace(PromptTemplate=_FakePromptTemplate)
    fake_langchain_parsers = types.SimpleNamespace(StrOutputParser=lambda: object())

    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "langchain_community.llms", fake_langchain_llms)
    monkeypatch.setitem(sys.modules, "langchain_core.prompts", fake_langchain_prompts)
    monkeypatch.setitem(sys.modules, "langchain_core.output_parsers", fake_langchain_parsers)

    payload = provider.invoke(PipelineRequest(prompt="hello", context={"k": "v"}))

    assert payload["assistant_text"] == ""
    assert "result" not in payload
    assert payload["notes"] == ["non_json_fallback"]
    assert payload["meta"]["provider"] == "huggingface_langchain:non_json_fallback"
    assert payload["meta"]["debug"]["raw_payload_preview"] == "plain text response"
    assert payload["meta"]["model"] == "demo/model"


def test_huggingface_bootstrap_requires_model_id() -> None:
    bootstrap = HuggingFaceModelBootstrap(model_id="")

    with pytest.raises(ValueError, match="model_id must be configured"):
        bootstrap.ensure_model()


def test_ollama_provider_normalizes_endpoint_to_chat() -> None:
    provider = OllamaProvider(endpoint="http://localhost:11434/api/generate", model_id="llama3.1")

    assert provider._resolve_chat_endpoint("http://localhost:11434/api/generate") == "http://localhost:11434/api/chat"
    assert provider._resolve_chat_endpoint("http://localhost:11434/api/chat") == "http://localhost:11434/api/chat"
    assert provider._resolve_chat_endpoint("http://localhost:11434") == "http://localhost:11434/api/chat"


def test_sanitize_context_allowlists_keys_and_limits_message_count() -> None:
    context = {
        "chat_id": 12,
        "class_id": 34,
        "ignored": "value",
        "messages": [
            {"role": "user", "content": "m1"},
            {"role": "assistant", "content": "m2"},
            {"role": "user", "content": "m3"},
            {"role": "assistant", "content": "m4"},
            {"role": "user", "content": "m5"},
        ],
    }

    sanitized = _sanitize_context(context)

    assert sanitized["chat_id"] == 12
    assert sanitized["class_id"] == 34
    assert "ignored" not in sanitized
    assert len(sanitized["messages"]) == 4
    assert sanitized["messages"][0]["content"] == "m2"
    assert sanitized["messages"][-1]["content"] == "m5"


def test_ollama_provider_builds_structured_chat_messages() -> None:
    provider = OllamaProvider(endpoint="http://localhost:11434", model_id="llama3.1")
    request = PipelineRequest(
        prompt="Explain ATP",
        context={"chat_id": 7, "class_id": 3, "messages": [{"role": "user", "content": "prior"}]},
    )

    messages = provider._build_messages(request)

    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert "assistant_text" in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "Explain ATP"}
    assert messages[2]["role"] == "system"
    assert '"chat_id": 7' in messages[2]["content"]
