from __future__ import annotations

from typing import Any


class ModelSelectionError(ValueError):
    pass


def normalize_model_id(model_id: str) -> str:
    return str(model_id or "").strip()


def resolve_provider_model_selection(
    payload: dict[str, Any],
    ai_service: Any,
    *,
    allow_session: bool = True,
    require_explicit: bool = False,
    inventory_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    _ = ai_service, allow_session, require_explicit, inventory_payload
    model_id = normalize_model_id(payload.get("model_id") or payload.get("model") or "")
    if not model_id:
        raise ModelSelectionError("model_id is required")
    return {"provider": "huggingface", "model_id": model_id, "source": "request_override"}


def resolve_catalog_selection(
    *,
    persisted_selection: dict[str, Any] | None,
    active_user_id: int | None,
    active_session_id: int | None,
    config_provider: str,
    config_model_id: str,
    available_by_provider: dict[str, set[str]],
    ordered_models: list[dict[str, Any]],
) -> dict[str, str]:
    _ = persisted_selection, active_user_id, active_session_id, available_by_provider, ordered_models
    return {
        "provider": str(config_provider or "huggingface"),
        "model_id": normalize_model_id(config_model_id),
        "source": "config_default",
    }
