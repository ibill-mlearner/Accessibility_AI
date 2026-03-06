from __future__ import annotations

from typing import Any

from flask import current_app, jsonify

from ..services.ai_pipeline.exceptions import AIPipelineUpstreamError
from ..services.ai_pipeline.model_catelog import family_id_from_model_id
from ..services.ai_pipeline.types import AIPipelineRequest
from ..helpers.ai_interaction_helpers import _extract_available_model_ids, _resolve_system_instructions, resolve_model_selection
from ..api.v1.routes import BadRequestError

def compose_system_prompt(
        system_instructions: str,
        payload: dict[str, Any]
    ) -> str | None:

    configured_guardrail = str(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT") or "").strip()
    request_system_prompt = str(payload.get("system_prompt") or "").strip()
    parts = [configured_guardrail, (system_instructions or "").strip(), request_system_prompt]
    combined = "\n\n".join(part for part in parts if part)
    return combined or None

def build_prompt_and_messages(
        payload: dict[str, Any]
    ):
    #  -> tuple[str, list[dict[str, Any]]] i don't think i had the return expectation right
    # at least it doesn't affect logic but i should get it right
    prompt = (payload.get("prompt") or "").strip()
    raw_messages = payload.get("messages")
    messages = raw_messages if isinstance(raw_messages, list) else []

    if not prompt:
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if (message.get("role") or "").lower() != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                prompt = content.strip()
                break

    return prompt, messages


def build_context_and_system_instructions(
    payload: dict[str, Any], messages: list[dict[str, Any]]
) -> tuple[dict[str, Any], str]:
    system_instructions = _resolve_system_instructions(payload)

    context_payload = payload.get("context")
    if not isinstance(context_payload, dict):
        context_payload = {}
    if messages and "messages" not in context_payload:
        context_payload["messages"] = messages

    return context_payload, system_instructions


def resolve_model_override(
        payload: dict[str, Any],
        ai_service: Any,
        context_payload: dict[str, Any],
        request_id: str
    ) -> None:

    override_provider = str(payload.get("provider") or "").strip().lower()
    override_model_id = str(payload.get("model_id") or "").strip()
    override_family_id = str(payload.get("family_id") or "").strip()
    override_provider_preference = (
        str(payload.get("provider_preference") or "").strip().lower() or "any"
    )

    has_direct_override = bool(override_provider or override_model_id)
    has_family_override = bool(override_family_id)
    if has_direct_override or has_family_override:
        if bool(override_provider) != bool(override_model_id):
            raise BadRequestError("provider and model_id must be supplied together")
        if has_direct_override and has_family_override:
            raise BadRequestError(
                "Provide either provider/model_id overrides or family_id override"
            )

    if not (has_direct_override or has_family_override):
        return

    available_by_provider = _extract_available_model_ids(ai_service.list_available_models())
    try:
        if has_direct_override:
            resolved_model_selection = resolve_model_selection(
                provider=override_provider,
                model_id=override_model_id,
                available_model_ids=available_by_provider,
            )
        else:
            resolved_model_selection = resolve_model_selection(
                family_id=override_family_id,
                provider_preference=override_provider_preference,
                available_model_ids=available_by_provider,
            )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    current_app.logger.debug(
        "api.ai_interactions.create.override_resolved request_id=%s provider=%s model_id=%s family_id=%s provider_preference=%s",
        request_id,
        resolved_model_selection.get("provider"),
        resolved_model_selection.get("model_id"),
        resolved_model_selection.get("family_id")
        or family_id_from_model_id(resolved_model_selection.get("model_id") or ""),
        override_provider_preference,
    )

    runtime_selection_meta = context_payload.get("runtime_model_selection")
    if not isinstance(runtime_selection_meta, dict):
        runtime_selection_meta = {}
        context_payload["runtime_model_selection"] = runtime_selection_meta
    runtime_selection_meta.update(
        {
            "provider": resolved_model_selection.get("provider"),
            "model_id": resolved_model_selection.get("model_id"),
            "family_id": resolved_model_selection.get("family_id")
            or family_id_from_model_id(resolved_model_selection.get("model_id") or ""),
            "source": "request_override",
        }
    )


def run_pipeline(
        ai_service: Any,
        dto: AIPipelineRequest,
        request_id: str,
        prompt: str
    ) -> Any:

    try:
        return ai_service.run(dto)
    except AIPipelineUpstreamError as exc:
        current_app.logger.warning(
            "api.ai_interactions.ai_service.run.error request_id=%s provider=%s model=%s upstream_source=%s error_type=%s prompt_preview=%r",
            request_id,
            current_app.config.get("AI_PROVIDER"),
            current_app.config.get("AI_MODEL_NAME"),
            (exc.details or {}).get("source", "unknown"),
            exc.__class__.__name__,
            prompt[:200],
        )
        return (
            jsonify(
                {
                    "error": {
                        "code": "upstream_error",
                        "message": str(exc),
                        "details": exc.details,
                    }
                }
            ),
            502,
        )
