from __future__ import annotations

from typing import Any

from flask import current_app, jsonify

from ...services.ai_pipeline_v2.interfaces import AIPipelineServiceInterface
from ...utils.ai_checker import (
    _extract_available_model_ids,
    resolve_model_override,
    resolve_model_selection,
    validate_runtime_model_selection,
)
from .interfaces import AIInteractionModelResolverInterface


class AIInteractionModelResolver(AIInteractionModelResolverInterface):
    """Default runtime provider/model resolver."""

    def resolve_runtime_model_selection(
        self,
        payload: dict[str, Any],
        ai_service: AIPipelineServiceInterface,
        context_payload: dict[str, Any],
        request_id: str,
    ):
        preflight_error = validate_runtime_model_selection(payload, ai_service)
        if preflight_error is not None:
            return jsonify(preflight_error[0]), preflight_error[1]

        available_by_provider = _extract_available_model_ids(ai_service.list_available_models())

        resolve_model_override(payload, ai_service, context_payload, request_id)

        runtime_selection = context_payload.get("runtime_model_selection")
        if isinstance(runtime_selection, dict) and runtime_selection.get("provider") and runtime_selection.get("model_id"):
            return None

        default_provider = str(current_app.config.get("AI_PROVIDER") or "").strip().lower()
        if default_provider == "ollama":
            default_model_id = str(current_app.config.get("AI_OLLAMA_MODEL") or current_app.config.get("AI_MODEL_NAME") or "").strip()
        else:
            default_model_id = str(current_app.config.get("AI_MODEL_NAME") or "").strip()

        try:
            resolved_default = resolve_model_selection(
                provider=default_provider,
                model_id=default_model_id,
                available_model_ids=available_by_provider,
            )
        except ValueError as exc:
            available_models = sorted(available_by_provider.get(default_provider, set()))
            return (
                jsonify(
                    {
                        "error": {
                            "code": "invalid_model_selection",
                            "message": str(exc),
                            "details": {
                                "provider": default_provider,
                                "model_id": default_model_id,
                                "source": "default_model_preflight",
                                "available_models": available_models,
                                "available_by_provider": {
                                    provider: sorted(model_ids)
                                    for provider, model_ids in available_by_provider.items()
                                },
                            },
                        }
                    }
                ),
                400,
            )

        context_payload["runtime_model_selection"] = {
            "provider": resolved_default["provider"],
            "model_id": resolved_default["model_id"],
            "family_id": resolved_default.get("family_id"),
            "source": "config_default",
        }
        return None


def resolve_runtime_model_selection(
    payload: dict[str, Any],
    ai_service: AIPipelineServiceInterface,
    context_payload: dict[str, Any],
    request_id: str,
):
    return AIInteractionModelResolver().resolve_runtime_model_selection(
        payload,
        ai_service,
        context_payload,
        request_id,
    )
