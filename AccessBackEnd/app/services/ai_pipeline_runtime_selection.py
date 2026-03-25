from __future__ import annotations

from typing import Any

from flask import current_app, session

from .ai_pipeline_contracts import AIPipelineServiceInterface


class ModelSelectionError(ValueError):
    def __init__(self, payload: dict[str, Any], status_code: int = 400) -> None:
        super().__init__(str(payload))
        self.payload = payload
        self.status_code = status_code


def normalize_provider_name(provider: str | None) -> str:
    return str(provider or "huggingface").strip().lower() or "huggingface"


def normalize_model_id(model_id: str | None) -> str:
    return str(model_id or "").strip()


def extract_huggingface_model_id_map(payload: dict[str, Any], *, normalize=normalize_model_id) -> dict[str, set[str]]:
    buckets = {
        "local": "huggingface",
        "huggingface_local": "huggingface",
        "ollama": "ollama",
    }
    result: dict[str, set[str]] = {"huggingface": set(), "ollama": set()}
    for bucket, provider in buckets.items():
        data = payload.get(bucket)
        if not isinstance(data, dict):
            continue
        models = data.get("models")
        if not isinstance(models, list):
            continue
        for model in models:
            if not isinstance(model, dict):
                continue
            model_id = normalize(str(model.get("id") or ""))
            if model_id:
                result[provider].add(model_id)
    return result


def _selection_error(provider: str, model_id: str, source: str, available_by_provider: dict[str, set[str]]) -> ModelSelectionError:
    available_models = sorted(available_by_provider.get(provider, set()))
    return ModelSelectionError(
        {
            "error": {
                "code": "invalid_model_selection",
                "message": "Unsupported provider/model selection",
                "details": {
                    "provider": provider,
                    "model_id": model_id,
                    "source": source,
                    "available_models": available_models,
                    "available_by_provider": {
                        key: sorted(value) for key, value in available_by_provider.items()
                    },
                },
            }
        },
        400,
    )


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
    if isinstance(persisted_selection, dict):
        persisted_provider = normalize_provider_name(persisted_selection.get("provider"))
        persisted_model = normalize_model_id(persisted_selection.get("model_id"))
        same_user = not active_user_id or int(persisted_selection.get("user_id") or active_user_id) == int(active_user_id)
        same_session = not active_session_id or persisted_selection.get("auth_session_id") == active_session_id
        if same_user and same_session and persisted_model in available_by_provider.get(persisted_provider, set()):
            return {"provider": persisted_provider, "model_id": persisted_model, "source": "session_selection"}

    cfg_provider = normalize_provider_name(config_provider)
    cfg_model = normalize_model_id(config_model_id)
    if cfg_model and cfg_model in available_by_provider.get(cfg_provider, set()):
        return {"provider": cfg_provider, "model_id": cfg_model, "source": "config_default"}

    first = ordered_models[0] if ordered_models else {"provider": cfg_provider, "id": cfg_model}
    return {
        "provider": normalize_provider_name(first.get("provider")),
        "model_id": normalize_model_id(first.get("id") or first.get("model_id")),
        "source": "catalog_fallback",
    }


def resolve_provider_model_selection(
    payload: dict[str, Any],
    ai_service: AIPipelineServiceInterface,
    *,
    allow_session: bool = True,
    require_explicit: bool = False,
) -> dict[str, str]:
    available_by_provider = extract_huggingface_model_id_map(ai_service.list_available_models())

    requested_provider = normalize_provider_name(payload.get("provider")) if payload.get("provider") else ""
    requested_model = normalize_model_id(payload.get("model_id")) if payload.get("model_id") else ""
    if requested_provider and requested_model:
        if requested_model not in available_by_provider.get(requested_provider, set()):
            raise _selection_error(requested_provider, requested_model, "request_override", available_by_provider)
        return {"provider": requested_provider, "model_id": requested_model, "source": "request_override"}

    if require_explicit:
        raise ModelSelectionError(
            {
                "error": {
                    "code": "invalid_model_selection",
                    "message": "provider and model_id are required",
                    "details": {},
                }
            },
            400,
        )

    if allow_session:
        persisted = session.get("ai_model_selection") if hasattr(session, "get") else None
        if isinstance(persisted, dict):
            persisted_provider = normalize_provider_name(persisted.get("provider"))
            persisted_model = normalize_model_id(persisted.get("model_id"))
            if persisted_model in available_by_provider.get(persisted_provider, set()):
                return {"provider": persisted_provider, "model_id": persisted_model, "source": "session_selection"}

    cfg_provider = normalize_provider_name(current_app.config.get("AI_PROVIDER"))
    cfg_model = normalize_model_id(current_app.config.get("AI_MODEL_NAME"))
    if cfg_model and cfg_model in available_by_provider.get(cfg_provider, set()):
        return {"provider": cfg_provider, "model_id": cfg_model, "source": "config_default"}

    fallback_model = sorted(available_by_provider.get(cfg_provider, set()))
    if fallback_model:
        return {"provider": cfg_provider, "model_id": fallback_model[0], "source": "provider_fallback"}

    if available_by_provider.get("huggingface"):
        return {
            "provider": "huggingface",
            "model_id": sorted(available_by_provider["huggingface"])[0],
            "source": "inventory_fallback",
        }

    return {"provider": cfg_provider or "huggingface", "model_id": cfg_model, "source": "config_default"}
