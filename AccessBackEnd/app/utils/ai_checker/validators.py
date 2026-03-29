from __future__ import annotations

from typing import Any

from .interfaces import AIInteractionEnvelope


class ModelSelectionError(ValueError):
    def __init__(self, payload: dict[str, Any], status_code: int = 400) -> None:
        super().__init__(str(payload))
        self.payload = payload
        self.status_code = status_code


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

        marker = "models--"
        lower_compact = compact.lower()
        if marker in lower_compact:
            marker_index = lower_compact.rfind(marker)
            token = compact[marker_index + len(marker):]
            token = token.split("/snapshots/", 1)[0]
            token = token.split("/refs/", 1)[0]
            token = token.split("/", 1)[0]
            return token.replace("--", "/")

        return compact



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

    @staticmethod
    def available_huggingface_model_ids(inventory: dict[str, Any]) -> set[str]:
        buckets = ("local", "huggingface_local")
        model_ids: set[str] = set()
        for bucket in buckets:
            models = inventory.get(bucket, {}).get("models", []) if isinstance(inventory, dict) else []
            if not isinstance(models, list):
                continue
            for model in models:
                if isinstance(model, dict):
                    model_id = AIInteractionValidator.to_clean_text(model.get("id"))
                    if model_id:
                        model_ids.add(model_id)
        return model_ids

    @staticmethod
    def resolve_model_selection(
        payload: dict[str, Any],
        *,
        inventory: dict[str, Any],
        persisted: dict[str, Any] | None = None,
        config_provider: str = "huggingface",
        config_model_id: str = "",
        require_explicit: bool = False,
    ) -> dict[str, str]:
        available = AIInteractionValidator.available_huggingface_model_ids(inventory)
        requested_model = AIInteractionValidator.to_clean_text(payload.get("model_id"))
        if requested_model:
            if requested_model in available:
                return {"provider": "huggingface", "model_id": requested_model, "source": "request_override"}
            raise ModelSelectionError({"error": {"code": "invalid_model_selection", "message": "Unsupported model selection", "details": {"model_id": requested_model}}}, 400)
        if require_explicit:
            raise ModelSelectionError({"error": {"code": "invalid_model_selection", "message": "model_id is required", "details": {}}}, 400)
        if isinstance(persisted, dict):
            persisted_model = AIInteractionValidator.to_clean_text(persisted.get("model_id"))
            if persisted_model and persisted_model in available:
                return {"provider": "huggingface", "model_id": persisted_model, "source": "session_selection"}
        config_model = AIInteractionValidator.to_clean_text(config_model_id)
        if config_model and (not available or config_model in available):
            return {"provider": "huggingface", "model_id": config_model, "source": "config_default"}
        fallback = next(iter(available), "")
        return {"provider": AIInteractionValidator.to_clean_text(config_provider, lower=True) or "huggingface", "model_id": fallback, "source": "catalog_fallback"}
