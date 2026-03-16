from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import current_app, has_request_context, session
from flask_login import current_user

from .interfaces import AIPipelineServiceInterface


@dataclass(slots=True)
class ModelSelectionError(Exception):
    payload: dict[str, Any]
    status_code: int = 400


def _invalid_selection_payload(*, message: str, provider: str = "", model_id: str = "", source: str, available_by_provider: dict[str, set[str]]) -> dict[str, Any]:
    return {
        "error": {
            "code": "invalid_model_selection",
            "message": message,
            "details": {
                "provider": provider,
                "model_id": model_id,
                "source": source,
                "available_models": sorted(available_by_provider.get(provider, set())) if provider else [],
                "available_by_provider": {key: sorted(value) for key, value in available_by_provider.items()},
            },
        }
    }


def _extract_available_model_ids(payload: dict[str, Any]) -> dict[str, set[str]]:
    provider_models: dict[str, set[str]] = {"huggingface": set()}

    for provider, top_key in (("huggingface", "huggingface_local"),):
        provider_payload = payload.get(top_key)
        if not isinstance(provider_payload, dict):
            continue
        models = provider_payload.get("models")
        if not isinstance(models, list):
            continue
        for model in models:
            if not isinstance(model, dict):
                continue
            model_id = str(model.get("id") or "").strip().lower()
            if model_id:
                provider_models[provider].add(model_id)
    return provider_models


def _resolve_session_model_selection() -> dict[str, str] | None:
    if not has_request_context():
        return None
    persisted = session.get("ai_model_selection")
    if not isinstance(persisted, dict):
        return None

    persisted_user_id = persisted.get("user_id")
    active_user_id = getattr(current_user, "id", None)
    if persisted_user_id is None or active_user_id is None:
        return None
    if int(persisted_user_id) != int(active_user_id):
        return None

    persisted_session_id = persisted.get("auth_session_id")
    active_session_id = session.get("auth_session_id")
    if persisted_session_id and active_session_id and int(persisted_session_id) != int(active_session_id):
        return None

    provider = str(persisted.get("provider") or "").strip().lower()
    model_id = str(persisted.get("model_id") or "").strip()
    if not provider or not model_id:
        return None
    return {"provider": provider, "model_id": model_id}


def _resolve_config_default() -> dict[str, str]:
    model_id = str(current_app.config.get("AI_MODEL_NAME") or "").strip()
    return {"provider": "huggingface", "model_id": model_id}


def _resolve_candidate(payload: dict[str, Any], *, allow_session: bool, require_explicit: bool) -> tuple[dict[str, str], str]:
    override_provider = str(payload.get("provider") or "").strip().lower()
    override_model_id = str(payload.get("model_id") or "").strip()
    deprecated_family_id = str(payload.get("family_id") or "").strip()
    deprecated_provider_preference = str(payload.get("provider_preference") or "").strip()

    if deprecated_family_id or deprecated_provider_preference:
        raise ValueError("family_id/provider_preference overrides are deprecated; provide provider and model_id")

    has_direct_override = bool(override_provider or override_model_id)
    if bool(override_provider) != bool(override_model_id):
        raise ValueError("provider and model_id must be supplied together")

    if has_direct_override:
        return {"provider": override_provider, "model_id": override_model_id}, "request_override"

    if require_explicit:
        raise ValueError("Provide provider and model_id")

    if allow_session:
        session_selection = _resolve_session_model_selection()
        if session_selection is not None:
            return session_selection, "session_selection"

    return _resolve_config_default(), "config_default"


def resolve_provider_model_selection(
    payload: dict[str, Any],
    ai_service: AIPipelineServiceInterface,
    *,
    allow_session: bool = True,
    require_explicit: bool = False,
    inventory_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    available_by_provider = _extract_available_model_ids(inventory_payload if isinstance(inventory_payload, dict) else ai_service.list_available_models())
    provider = ""
    model_id = ""
    source = "unknown"
    try:
        candidate, source = _resolve_candidate(payload, allow_session=allow_session, require_explicit=require_explicit)
        provider = str(candidate.get("provider") or "").strip().lower()
        model_id = str(candidate.get("model_id") or "").strip()
        if provider != "huggingface":
            raise ValueError("Unsupported provider: only huggingface is allowed")
        if model_id.lower() not in available_by_provider.get(provider, set()):
            raise ValueError(f"Model not available for provider {provider}: {model_id}")
    except ValueError as exc:
        raise ModelSelectionError(
            _invalid_selection_payload(
                message=str(exc),
                provider=provider,
                model_id=model_id,
                source=source,
                available_by_provider=available_by_provider,
            )
        ) from exc

    return {
        "provider": provider,
        "model_id": model_id,
        "source": source,
    }
