from __future__ import annotations

from typing import Any

from flask import current_app, session
from flask_login import current_user


class ModelSelectionError(ValueError):
    def __init__(self, payload: dict[str, Any], status_code: int = 400):
        super().__init__(payload.get("error", {}).get("message", "Invalid model selection"))
        self.payload = payload
        self.status_code = status_code


def normalize_provider_name(value: object) -> str:
    _ = value
    return "huggingface"


def normalize_model_id(model_id: object) -> str:
    return str(model_id or "").strip().lower()


def _available_model_ids(ai_service: Any) -> set[str]:
    payload = ai_service.list_available_models() if hasattr(ai_service, "list_available_models") else {}
    local = payload.get("local") if isinstance(payload, dict) else {}
    legacy = payload.get("huggingface_local") if isinstance(payload, dict) else {}
    models = local.get("models") if isinstance(local, dict) and isinstance(local.get("models"), list) else legacy.get("models") if isinstance(legacy, dict) and isinstance(legacy.get("models"), list) else []
    return {normalize_model_id(model.get("id")) for model in models if isinstance(model, dict) and normalize_model_id(model.get("id"))}


def _bad_selection(message: str, *, provider: str, model_id: str, source: str, available_models: list[str]) -> ModelSelectionError:
    payload = {
        "error": {
            "code": "invalid_model_selection",
            "message": message,
            "details": {
                "provider": provider,
                "model_id": model_id,
                "source": source,
                "available_models": available_models,
                "available_by_provider": {"huggingface": available_models},
            },
        }
    }
    return ModelSelectionError(payload, 400)


def resolve_provider_model_selection(
    payload: dict[str, Any],
    ai_service: Any,
    *,
    allow_session: bool = True,
    require_explicit: bool = False,
) -> dict[str, str]:
    request_provider = str(payload.get("provider") or "").strip().lower()
    request_model_id = str(payload.get("model_id") or "").strip()

    source = "request_override"
    provider = request_provider or "huggingface"
    model_id = request_model_id

    if allow_session and (not provider or not model_id):
        persisted = session.get("ai_model_selection")
        if isinstance(persisted, dict):
            active_user_id = getattr(current_user, "id", None)
            if active_user_id is not None and int(persisted.get("user_id") or -1) == int(active_user_id):
                source = "session_selection"
                provider = str(persisted.get("provider") or provider).strip().lower() or "huggingface"
                model_id = str(persisted.get("model_id") or model_id).strip()

    if require_explicit and not request_model_id:
        raise _bad_selection(
            "model_id is required",
            provider=provider,
            model_id=model_id,
            source=source,
            available_models=sorted(_available_model_ids(ai_service)),
        )

    if provider != "huggingface":
        raise _bad_selection(
            "Unsupported provider: only huggingface is allowed",
            provider=provider,
            model_id=model_id,
            source=source,
            available_models=sorted(_available_model_ids(ai_service)),
        )

    if not model_id:
        model_id = str(current_app.config.get("AI_MODEL_NAME") or "").strip()
        source = "config_default"

    available_models = sorted(_available_model_ids(ai_service))
    if available_models and normalize_model_id(model_id) not in set(available_models):
        raise _bad_selection(
            "Requested model is not available",
            provider=provider,
            model_id=model_id,
            source=source,
            available_models=available_models,
        )

    return {
        "provider": "huggingface",
        "model_id": model_id,
        "source": source,
    }


def resolve_catalog_selection(
    *,
    persisted_selection: dict[str, Any] | None,
    active_user_id: int | None,
    active_session_id: Any,
    config_provider: str,
    config_model_id: str,
    available_by_provider: dict[str, set[str]],
    ordered_models: list[dict[str, Any]],
) -> dict[str, str]:
    _ = config_provider, active_session_id
    available_models = available_by_provider.get("huggingface") or {
        normalize_model_id(model.get("id"))
        for model in ordered_models
        if isinstance(model, dict) and str(model.get("provider") or "").strip().lower() == "huggingface"
    }

    if isinstance(persisted_selection, dict) and active_user_id is not None:
        if int(persisted_selection.get("user_id") or -1) == int(active_user_id):
            model_id = str(persisted_selection.get("model_id") or "").strip()
            if model_id and (not available_models or normalize_model_id(model_id) in available_models):
                return {"provider": "huggingface", "id": model_id, "source": "session_selection"}

    resolved_default = str(config_model_id or "").strip()
    if resolved_default:
        return {"provider": "huggingface", "id": resolved_default, "source": "config_default"}

    first = next((model for model in ordered_models if isinstance(model, dict)), {})
    return {
        "provider": "huggingface",
        "id": str(first.get("id") or "").strip(),
        "source": "catalog_first",
    }


def extract_huggingface_model_id_map(payload: dict[str, Any], normalize=normalize_model_id) -> dict[str, set[str]]:
    local = payload.get("local") if isinstance(payload.get("local"), dict) else {}
    legacy = payload.get("huggingface_local") if isinstance(payload.get("huggingface_local"), dict) else {}
    models = local.get("models") if isinstance(local.get("models"), list) else legacy.get("models") if isinstance(legacy.get("models"), list) else []
    result = {"huggingface": set()}
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = normalize(model.get("id"))
        if model_id:
            result["huggingface"].add(model_id)
    return result
