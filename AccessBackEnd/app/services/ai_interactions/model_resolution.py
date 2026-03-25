from __future__ import annotations

from flask import jsonify

from ...services.ai_pipeline_contracts import AIPipelineServiceInterface
from ...services.ai_pipeline_runtime_selection import ModelSelectionError, resolve_provider_model_selection
from .interfaces import AIInteractionModelResolverInterface


class AIInteractionModelResolver(AIInteractionModelResolverInterface):
    """Default runtime provider/model resolver."""

    def resolve_runtime_model_selection(
        self,
        payload: dict,
        ai_service: AIPipelineServiceInterface,
        context_payload: dict,
        request_id: str,
    ):
        _ = request_id
        try:
            resolved = resolve_provider_model_selection(payload, ai_service)
        except ModelSelectionError as exc:
            return jsonify(exc.payload), exc.status_code
        context_payload["runtime_model_selection"] = resolved
        return None


def resolve_runtime_model_selection(
    payload: dict,
    ai_service: AIPipelineServiceInterface,
    context_payload: dict,
    request_id: str,
):
    return AIInteractionModelResolver().resolve_runtime_model_selection(
        payload,
        ai_service,
        context_payload,
        request_id,
    )
