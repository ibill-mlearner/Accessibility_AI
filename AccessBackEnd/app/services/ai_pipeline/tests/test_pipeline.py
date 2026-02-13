from __future__ import annotations

import pytest

from app.services.ai_pipeline.pipeline import AIPipelineConfig, AIPipelineService


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
