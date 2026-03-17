from __future__ import annotations

from typing import Any

from flask import current_app, session


class ModelSelectionError(ValueError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = {
            "error": {
                "code": "invalid_model_selection",
                "message": message,
                "details": details or {},
            }
        }


def normalize_model_id(model_id: str) -> str:
    candidate = str(model_id or "").strip().lower()
    if not candidate:
        return ""

    marker = "models--"
    if marker in candidate:
        token = candidate.split(marker, 1)[1]
        token = token.split("/snapshots/", 1)[0]
        token = token.split("/refs/", 1)[0]
        token = token.split("/", 1)[0]
        parts = [part for part in token.split("--") if part]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return token

    return candidate


def extract_available_model_ids(inventory_payload: dict[str, Any] | None) -> dict[str, set[str]]:
    extracted: dict[str, set[str]] = {}
    if not isinstance(inventory_payload, dict):
        return extracted

    for provider, payload in inventory_payload.items():
        if provider == "models":
            continue
        if not isinstance(payload, dict):
            continue
        models = payload.get("models")
        if not isinstance(models, list):
            continue

        canonical_provider = "huggingface" if provider in {"huggingface_local", "local"} else str(provider).strip().lower()
        bucket = extracted.setdefault(canonical_provider, set())

        for model in models:
            if not isinstance(model, dict):
                continue
            raw_id = str(model.get("id") or "").strip()
            canonical_id = normalize_model_id(raw_id)
            if canonical_id:
                bucket.add(canonical_id)

    return extracted


def _resolve_session_model_selection() -> dict[str, str] | None:
    selection = session.get("ai_model_selection")
    if not isinstance(selection, dict):
        return None
    provider = str(selection.get("provider") or "").strip().lower()
    model_id = normalize_model_id(str(selection.get("model_id") or "").strip())
    if not provider or not model_id:
        return None
    return {"provider": provider, "model_id": model_id}


def resolve_provider_model_selection(
    payload: dict[str, Any],
    ai_service: Any,
    *,
    allow_session: bool = True,
    require_explicit: bool = False,
    inventory_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    if payload.get("family_id") or payload.get("provider_preference"):
        raise ModelSelectionError("Deprecated model selection fields are no longer supported")

    provider = str(payload.get("provider") or "").strip().lower()
    model_id = str(payload.get("model_id") or payload.get("model") or "").strip()

    inventory = inventory_payload
    if inventory is None and hasattr(ai_service, "list_available_models"):
        inventory = ai_service.list_available_models()
    available = extract_available_model_ids(inventory)

    if model_id:
        selected_provider = provider or str(current_app.config.get("AI_PROVIDER") or "huggingface").strip().lower()
        canonical_provider = "huggingface" if selected_provider in {"huggingface_local", "local"} else selected_provider
        allowed = available.get(canonical_provider, set())
        normalized_request = normalize_model_id(model_id)
        if canonical_provider in available and normalized_request not in allowed:
            raise ModelSelectionError(
                "Requested model is not available for the selected provider",
                details={"provider": selected_provider, "model_id": model_id, "available_models": sorted(allowed)},
            )
        return {"provider": selected_provider, "model_id": normalized_request, "source": "request_override"}

    if allow_session:
        session_selection = _resolve_session_model_selection()
        if session_selection is not None:
            return {**session_selection, "source": "session_selection"}

    config_provider = str(current_app.config.get("AI_PROVIDER") or "huggingface").strip().lower()
    config_model = normalize_model_id(str(current_app.config.get("AI_MODEL_NAME") or "").strip())

    if require_explicit and not config_model:
        raise ModelSelectionError("model_id is required", details={"provider": config_provider, "available_models": []})

    canonical_provider = "huggingface" if config_provider in {"huggingface_local", "local"} else config_provider
    allowed_defaults = available.get(canonical_provider, set())
    if canonical_provider in available and normalize_model_id(config_model) not in allowed_defaults:
        raise ModelSelectionError(
            "Configured default model is unavailable",
            details={"provider": config_provider, "available_models": sorted(allowed_defaults)},
        )

    return {"provider": config_provider or "huggingface", "model_id": config_model, "source": "config_default"}


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
    if isinstance(persisted_selection, dict):
        persisted_provider = str(persisted_selection.get("provider") or "").strip().lower()
        persisted_model_id = normalize_model_id(str(persisted_selection.get("model_id") or "").strip())
        persisted_user_id = persisted_selection.get("user_id")
        persisted_session_id = persisted_selection.get("auth_session_id")
        if (
            persisted_provider
            and persisted_model_id
            and (persisted_user_id is None or int(persisted_user_id) == int(active_user_id or 0))
            and (persisted_session_id is None or int(persisted_session_id) == int(active_session_id or 0))
            and normalize_model_id(persisted_model_id) in available_by_provider.get(persisted_provider, set())
        ):
            return {"provider": persisted_provider, "model_id": persisted_model_id, "source": "session_selection"}

    normalized_provider = str(config_provider or "huggingface").strip().lower()
    normalized_config_model = normalize_model_id(str(config_model_id or "").strip())

    if normalize_model_id(normalized_config_model) in available_by_provider.get(normalized_provider, set()):
        return {"provider": normalized_provider, "model_id": normalized_config_model, "source": "config_default"}

    for model in ordered_models:
        provider = str(model.get("provider") or "").strip().lower()
        model_id = normalize_model_id(str(model.get("id") or "").strip())
        if provider and model_id:
            return {"provider": provider, "model_id": model_id, "source": "db_first_available"}

    return {"provider": normalized_provider, "model_id": normalized_config_model, "source": "config_default"}
