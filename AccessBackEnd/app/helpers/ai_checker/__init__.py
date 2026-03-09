
from __future__ import annotations

from typing import Any

from .interfaces import AIInteractionEnvelope, AIInteractionMonolithInterface
from .validator import AIInteractionValidator


class AIInteractionMonolith(AIInteractionMonolithInterface):
    """Compressed helper that centralizes AI payload normalize/validate/mutate/check."""

    RESPONSE_KEYS = ("assistant_text", "result", "answer", "response_text", "response", "output", "text")

    def normalize(self, payload: Any) -> AIInteractionEnvelope:
        if isinstance(payload, AIInteractionEnvelope):
            return payload

        if isinstance(payload, str):
            envelope = AIInteractionEnvelope(prompt="", assistant_text=payload.strip())
            return envelope

        if not isinstance(payload, dict):
            return AIInteractionEnvelope(prompt="", assistant_text=str(payload or "").strip())

        candidate = next((payload.get(key) for key in self.RESPONSE_KEYS if payload.get(key) is not None), "")
        confidence = payload.get("confidence")
        notes = payload.get("notes")

        envelope = AIInteractionEnvelope(
            prompt=str(payload.get("prompt") or "").strip(),
            assistant_text=str(candidate or "").strip(),
            provider=str(payload.get("provider") or "").strip().lower(),
            model_id=str(payload.get("model_id") or "").strip(),
            confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
            notes=[str(note).strip() for note in notes] if isinstance(notes, list) else ([str(notes).strip()] if isinstance(notes, str) and notes.strip() else []),
            meta=payload.get("meta").copy() if isinstance(payload.get("meta"), dict) else {},
        )
        return envelope

    def validate(self, envelope: AIInteractionEnvelope) -> None:
        AIInteractionValidator.validate_envelope(envelope)

    def mutate(self, envelope: AIInteractionEnvelope, updates: dict[str, Any] | None = None) -> AIInteractionEnvelope:
        updates = updates or {}
        for key in ("prompt", "assistant_text", "provider", "model_id"):
            if key in updates:
                setattr(envelope, key, str(updates[key] or "").strip())

        if "confidence" in updates:
            value = updates.get("confidence")
            envelope.confidence = float(value) if isinstance(value, (int, float)) else None

        if "notes" in updates:
            notes = updates.get("notes")
            envelope.notes = [str(note).strip() for note in notes] if isinstance(notes, list) else []

        if "meta" in updates and isinstance(updates.get("meta"), dict):
            envelope.meta.update(updates["meta"])

        return envelope

    def check(self, envelope: AIInteractionEnvelope) -> dict[str, Any]:
        return AIInteractionValidator.check_envelope(envelope)


__all__ = [
    "AIInteractionEnvelope",
    "AIInteractionMonolithInterface",
    "AIInteractionMonolith",
    "AIInteractionValidator",
]