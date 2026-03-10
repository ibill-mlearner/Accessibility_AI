from __future__ import annotations

import json
from typing import Any

from .interfaces import AIInteractionEnvelope
from .validators import AIInteractionValidator


class AIInteractionMutations:
    """Mutation/transform helpers for AI payloads and responses."""

    @staticmethod
    def normalize_payload(payload: Any) -> AIInteractionEnvelope:
        if isinstance(payload, AIInteractionEnvelope):
            return payload
        if not isinstance(payload, dict):
            return AIInteractionEnvelope(prompt="", assistant_text=AIInteractionValidator.to_clean_text(payload))

        candidate = next((payload.get(key) for key in AIInteractionValidator.RESPONSE_KEYS if payload.get(key) is not None), "")
        return AIInteractionEnvelope(
            prompt=AIInteractionValidator.to_clean_text(payload.get("prompt")),
            assistant_text=AIInteractionValidator.to_clean_text(candidate),
            provider=AIInteractionValidator.to_clean_text(payload.get("provider"), lower=True),
            model_id=AIInteractionValidator.to_clean_text(payload.get("model_id")),
            confidence=AIInteractionValidator.to_optional_float(payload.get("confidence")),
            notes=AIInteractionValidator.to_clean_notes(payload.get("notes")),
            meta=payload.get("meta").copy() if isinstance(payload.get("meta"), dict) else {},
        )

    @staticmethod
    def mutate_envelope(envelope: AIInteractionEnvelope, updates: dict[str, Any] | None = None) -> AIInteractionEnvelope:
        for key, lower in (("prompt", False), ("assistant_text", False), ("provider", True), ("model_id", False)):
            if updates and key in updates:
                setattr(envelope, key, AIInteractionValidator.to_clean_text(updates.get(key), lower=lower))
        if updates and "confidence" in updates:
            envelope.confidence = AIInteractionValidator.to_optional_float(updates.get("confidence"))
        if updates and "notes" in updates:
            envelope.notes = AIInteractionValidator.to_clean_notes(updates.get("notes"))
        if updates and isinstance(updates.get("meta"), dict):
            envelope.meta.update(updates["meta"])
        return envelope

    @staticmethod
    def strip_prompt_template_echo(text: str) -> str:
        template_tokens = ("{prompt}", "{context}", "{question}", "{{", "}}")
        cleaned = "\n".join(
            line.strip()
            for line in str(text or "").splitlines()
            if line.strip() and not any(token in line.lower() for token in template_tokens)
        ).strip()
        return cleaned.removeprefix("Answer:").strip()

    @staticmethod
    def truncate_debug_payload(value: Any, *, limit: int = 1200) -> str:
        serialized = value if isinstance(value, str) else json.dumps(value, default=str)
        return serialized if len(serialized) <= limit else f"{serialized[:limit]}... [truncated]"