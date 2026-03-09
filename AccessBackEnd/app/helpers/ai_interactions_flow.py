from __future__ import annotations

from typing import Any

from flask import current_app, jsonify

from ..services.ai_pipeline.exceptions import AIPipelineUpstreamError
from ..services.ai_pipeline.interfaces import AIPipelineServiceInterface
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

def validate_runtime_model_selection(
    payload: dict[str, Any],
    ai_service: AIPipelineServiceInterface,
) -> tuple[dict[str, str], int] | None:
    """Validate provider/model_id request pair before invoking provider runtime."""
    provider = str(payload.get("provider") or "").strip().lower()
    model_id = str(payload.get("model_id") or "").strip()
    if not provider and not model_id:
        return None
    if bool(provider) != bool(model_id):
        raise BadRequestError("provider and model_id must be supplied together")

    available_by_provider = _extract_available_model_ids(ai_service.list_available_models())
    try:
        resolved = resolve_model_selection(
            provider=provider,
            model_id=model_id,
            available_model_ids=available_by_provider,
        )
    except ValueError as exc:
        return (
            {
                "error": {
                    "code": "invalid_model_id",
                    "message": str(exc),
                    "details": {
                        "provider": provider,
                        "model_id": model_id,
                        "source": "model_preflight",
                        "available_models": sorted(available_by_provider.get(provider, set())),
                    },
                }
            },
            400,
        )

    payload["provider"] = resolved["provider"]
    payload["model_id"] = resolved["model_id"]
    return None


def classify_upstream_error(
    exc: AIPipelineUpstreamError,
    *,
    provider: str,
    model_id: str,
    request_id: str,
) -> tuple[str, int, dict[str, Any]]:
    details = exc.details if isinstance(exc.details, dict) else {}
    upstream_status = details.get("upstream_status")
    source = str(details.get("source") or "provider_runtime")
    message_lower = str(exc).lower()

    error_code = "upstream_error"
    status_code = 502

    if isinstance(upstream_status, int):
        if upstream_status in (401, 403):
            error_code = "provider_auth_failed"
            status_code = 502
        elif upstream_status == 404:
            error_code = "provider_model_not_found"
            status_code = 502

    if error_code == "upstream_error":
        if "gated" in message_lower and "model" in message_lower:
            error_code = "provider_gated_model"
            status_code = 502
        elif any(token in message_lower for token in ("unauthorized", "invalid token", "forbidden", "authentication")):
            error_code = "provider_auth_failed"
            status_code = 502
        elif any(token in message_lower for token in ("not found", "no such model", "404")):
            error_code = "provider_model_not_found"
            status_code = 502

    normalized_details = {
        **details,
        "source": source,
        "provider": provider or details.get("provider") or "unknown",
        "model_id": model_id or details.get("model_id") or "unknown",
        "upstream_status": upstream_status,
        "request_id": request_id,
    }
    return error_code, status_code, normalized_details



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
        ai_service: AIPipelineServiceInterface,
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
        ai_service: AIPipelineServiceInterface,
        dto: AIPipelineRequest,
        request_id: str,
        prompt: str
    ) -> Any:

    try:
        return ai_service.run(dto)
    except AIPipelineUpstreamError as exc:
        details = exc.details if isinstance(exc.details, dict) else {}
        error_code, status_code, normalized_details = classify_upstream_error(
            exc,
            provider=str(details.get("provider") or current_app.config.get("AI_PROVIDER") or ""),
            model_id=str(details.get("model_id") or current_app.config.get("AI_MODEL_NAME") or ""),
            request_id=request_id
        )
        current_app.logger.warning(
            "api.ai_interactions.failure request_id=%s provider=%s model_id=%s error_code=%s upstream_status=%s source=%s error_type=%s prompt_preview=%r",
            request_id,
            normalized_details.get("provider"),
            normalized_details.get("model_id"),
            error_code,
            normalized_details.get("upstream_status"),
            normalized_details.get("source"),
            exc.__class__.__name__,
            prompt[:200],
        )
        return (
            jsonify(
                {
                    "error": {
                        "code": error_code,
                        "message": str(exc),
                        "details": normalized_details,
                    }
                }
            ),
            502,
        )
