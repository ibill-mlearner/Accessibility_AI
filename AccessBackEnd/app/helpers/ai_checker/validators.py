from __future__ import annotations

from typing import Any

from .interfaces import AIInteractionEnvelope


class AIInteractionValidator:
    """Centralized validation/check helper to keep monolith logic compact."""

    REQUIRED_TEXT_FIELDS = ("prompt",)

    @staticmethod
    def validate_envelope(envelope: AIInteractionEnvelope) -> None:
        for field_name in AIInteractionValidator.REQUIRED_TEXT_FIELDS:
            if not str(getattr(envelope, field_name, "") or "").strip():
                raise ValueError(f"{field_name} is required")

        if envelope.confidence is not None and not isinstance(envelope.confidence, (int, float)):
            raise ValueError("confidence must be numeric")

    @staticmethod
    def check_envelope(envelope: AIInteractionEnvelope) -> dict[str, Any]:
        assistant_text = str(envelope.assistant_text or "").strip()
        return {
            "is_valid": bool(str(envelope.prompt or "").strip()),
            "assistant_has_text": bool(assistant_text),
            "provider": str(envelope.provider or "").strip().lower(),
            "model_id": str(envelope.model_id or "").strip(),
            "note_count": len(envelope.notes),
            "meta_keys": sorted(envelope.meta.keys()) if isinstance(envelope.meta, dict) else [],
        }