from __future__ import annotations

from typing import Any

from .interfaces import AIInteractionEnvelope


class AIInteractionValidator:
    """Centralized validation/check helper to keep monolith logic compact."""

    REQUIRED_TEXT_FIELDS = ("prompt",)
    RESPONSE_KEYS = ("assistant_text", "result", "answer", "response_text", "response", "output", "text")

    @staticmethod
    def to_clean_text(value: Any, *, lower: bool = False) -> str:
        text = str(value or "").strip()
        return text.lower() if lower else text

    @staticmethod
    def to_optional_float(value: Any) -> float | None:
        return float(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def to_clean_notes(value: Any) -> list[str]:
        if isinstance(value, list):
            return [AIInteractionValidator.to_clean_text(note) for note in value if AIInteractionValidator.to_clean_text(note)]
        if isinstance(value, str):
            note = AIInteractionValidator.to_clean_text(value)
            return [note] if note else []
        return []

    @staticmethod
    def to_clean_model_id(value: Any) -> str:
        text = AIInteractionValidator.to_clean_text(value)
        if not text:
            return ""
        normalized = text.replace("\\", "/")
        compact = normalized.rstrip("/")
        if compact.lower().startswith("models--"):
            return compact[len("models--"):].replace("--", "/")
        if "/" not in compact:
            return compact
        last_segment = compact.rsplit("/", 1)[-1].strip()
        if not last_segment:
            return compact
        if ":" in last_segment:
            return last_segment.lower()
        if "--" in last_segment and "models--" not in last_segment.lower():
            return last_segment.replace("--", "/")
        return last_segment


    @staticmethod
    def resolve_help_intent(value: Any, *, default: str = "summarization") -> str:
        intent = AIInteractionValidator.to_clean_text(value, lower=True)
        return intent or AIInteractionValidator.to_clean_text(default, lower=True)

    @staticmethod
    def validate_envelope(envelope: AIInteractionEnvelope) -> None:
        for field_name in AIInteractionValidator.REQUIRED_TEXT_FIELDS:
            if not AIInteractionValidator.to_clean_text(getattr(envelope, field_name, "")):
                raise ValueError(f"{field_name} is required")
        if envelope.confidence is not None and not isinstance(envelope.confidence, (int, float)):
            raise ValueError("confidence must be numeric")

    @staticmethod
    def check_envelope(envelope: AIInteractionEnvelope) -> dict[str, Any]:
        return {
            "is_valid": bool(AIInteractionValidator.to_clean_text(envelope.prompt)),
            "assistant_has_text": bool(AIInteractionValidator.to_clean_text(envelope.assistant_text)),
            "provider": AIInteractionValidator.to_clean_text(envelope.provider, lower=True),
            "model_id": AIInteractionValidator.to_clean_text(envelope.model_id),
            "note_count": len(envelope.notes),
            "meta_keys": sorted(envelope.meta.keys()) if isinstance(envelope.meta, dict) else [],
        }