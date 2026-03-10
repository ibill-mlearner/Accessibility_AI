from __future__ import annotations

from typing import Any

from flask import jsonify

from ...services.ai_pipeline.interfaces import AIPipelineServiceInterface
from ...utils.ai_checker import resolve_model_override, validate_runtime_model_selection
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

        resolve_model_override(payload, ai_service, context_payload, request_id)
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
