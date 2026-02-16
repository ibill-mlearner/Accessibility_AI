from __future__ import annotations

import json

import pytest

from app.services.ai_pipeline.bootstrap import HuggingFaceModelBootstrap
from app.services.ai_pipeline.providers import HTTPEndpointProvider, HuggingFaceLangChainProvider
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


def test_huggingface_provider_parse_json_raises_on_invalid_json() -> None:
    provider = HuggingFaceLangChainProvider(model_id="demo/model")

    with pytest.raises(ValueError, match="not valid JSON"):
        provider._parse_json("this is not json")


def test_huggingface_bootstrap_requires_model_id() -> None:
    bootstrap = HuggingFaceModelBootstrap(model_id="")

    with pytest.raises(ValueError, match="model_id must be configured"):
        bootstrap.ensure_model()
