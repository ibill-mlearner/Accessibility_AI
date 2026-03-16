from AccessBackEnd.app.services.ai_pipeline_v2.types import AIPipelineUpstreamError
from AccessBackEnd.app.utils.ai_checker import (
    AIInteractionEnvelope,
    AIInteractionMonolith,
    AIInteractionValidator,
    classify_upstream_error,
)

def test_monolith_normalize_and_check_compact_payload():
    monolith = AIInteractionMonolith()
    envelope = monolith.normalize(
        {
            "prompt": "Summarize this",
            "answer": "Done",
            "provider": "OpenAI",
            "model_id": "gpt-4o-mini",
            "confidence": 0.8,
            "notes": ["ok"],
            "meta": {"request_id": "abc"},
        }
    )

    assert isinstance(envelope, AIInteractionEnvelope)
    assert envelope.assistant_text == "Done"
    assert monolith.check(envelope)["assistant_has_text"] is True


def test_monolith_validate_and_mutate():
    monolith = AIInteractionMonolith()
    envelope = AIInteractionEnvelope(prompt="hello")

    monolith.validate(envelope)
    updated = monolith.mutate(envelope, {"assistant_text": "world", "meta": {"x": 1}})

    assert updated.assistant_text == "world"
    assert updated.meta["x"] == 1

    assert updated.meta["x"] == 1


def test_ai_checker_cleans_model_id_for_provider_errors():
    platform_agnostic_windows_path = r"AccessBackEnd\\instance\\models\\Qwen2.5-0.5B-Instruct"
    exc = AIPipelineUpstreamError(
        message="connection refused",
        details={"model_id": platform_agnostic_windows_path},
    )

    _code, _status, details = classify_upstream_error(
        exc,
        provider="ollama",
        model_id=platform_agnostic_windows_path,
        request_id="n/a",
    )

    assert details["model_id"] == "Qwen2.5-0.5B-Instruct"


def test_ai_checker_normalizes_cached_model_aliases():
    assert AIInteractionValidator.to_clean_model_id("models--Qwen--Qwen2.5-0.5B-Instruct") == "Qwen/Qwen2.5-0.5B-Instruct"
    assert AIInteractionValidator.to_clean_model_id(r"C:\models\qwen2.5:0.5b") == "qwen2.5:0.5b"