from __future__ import annotations

from flask import current_app, jsonify
from flask_login import login_required

from ...models import AIInteraction, Chat
from ...schemas.validation import AIInteractionPayloadSchema
from ...services.ai_pipeline_gateway import AIPipelineGateway
from ...utils.ai_checker.interaction_helpers import (
    derive_selection_from_chat,
    normalize_interaction_response,
    persist_interaction,
    prepare_interaction_inputs,
    resolve_chat_id,
    resolve_initiated_by,
)
from ...utils.chat_access import ChatAccessHelper
from .routes import (
    _assert_chat_permissions,
    _publish,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    api_v1_bp,
    db,
)


# Backwards-compatible test hook.
_derive_selection_from_chat = derive_selection_from_chat


def _log_payload(raw: dict, payload: dict) -> None:
    current_app.logger.debug("api.ai.interactions.payload.raw path=%s json_keys=%s", "/api/v1/ai/interactions", sorted(raw.keys()))
    current_app.logger.debug("api.ai.interactions.payload.validated keys=%s", sorted(payload.keys()))


def _log_request(payload: dict) -> None:
    current_app.logger.debug("api.ai_interactions.request method=%s path=%s json_keys=%s", "POST", "/api/v1/ai/interactions", sorted(payload.keys()))


def _log_interaction_start(payload: dict, request_id: str, prompt: str) -> None:
    current_app.logger.debug(
        "api.ai_interactions.create.start request_id=%s provider=%s model=%s timeout_seconds=%s prompt_len=%s messages_count=%s prompt_preview=%r",
        request_id,
        current_app.config.get("AI_PROVIDER"),
        current_app.config.get("AI_MODEL_NAME"),
        current_app.config.get("AI_TIMEOUT_SECONDS"),
        len(prompt),
        len(payload.get("messages")) if isinstance(payload.get("messages"), list) else 0,
        prompt[:200],
    )


def _publish_request_summary(prompt: str, messages: list[dict], payload: dict, system_prompt: str | None, system_instructions: bool) -> None:
    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_messages": bool(messages),
            "has_system_prompt": bool(payload.get("system_prompt")),
            "has_guardrail_system_prompt": bool(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT")),
            "has_db_system_instructions": system_instructions,
            "has_composed_system_prompt": bool(system_prompt),
        },
    )


def _run(ai_service: AIPipelineGateway, payload: dict, prepared: dict, chat_id: int | None, initiated_by: str):
    result = ai_service.run_interaction(
        prepared["prompt"],
        context=prepared["context_payload"],
        messages=prepared["messages"],
        system_prompt=prepared["system_prompt"],
        request_id=prepared["request_id"],
        chat_id=chat_id,
        initiated_by=initiated_by,
        class_id=payload.get("class_id"),
        user_id=payload.get("user_id"),
    )
    return normalize_interaction_response(result)


def _warn_if_empty_response(request_id: str, normalized_result: dict) -> None:
    if not normalized_result.get("assistant_text"):
        current_app.logger.warning(
            "api.ai_interactions.normalize.empty_assistant request_id=%s provider=%s model=%s notes_count=%s",
            request_id,
            normalized_result["meta"].get("provider"),
            normalized_result["meta"].get("model"),
            len(normalized_result.get("notes") or []),
        )


def _validate_interaction_payload() -> tuple[dict, dict]:
    raw = _read_json_object()
    payload = _validate_payload(raw, AIInteractionPayloadSchema())
    _log_payload(raw, payload)
    _log_request(payload)
    return raw, payload


@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    _raw, payload = _validate_interaction_payload()
    # INTEGRATION POINT (PromptContextAssemblerInterface):
    # This is the earliest API entry where request payload + DB session are available.
    # Route-level integration can inject/use a prompt context assembler before calling
    # prepare_interaction_inputs so feature/conversation/system prompt context is
    # composed through the shared DB interface contract.
    prepared = prepare_interaction_inputs(payload, db_session=db.session)
    _log_interaction_start(payload, prepared["request_id"], prepared["prompt"])
    _publish_request_summary(prepared["prompt"], prepared["messages"], payload, prepared["system_prompt"], bool(prepared["system_prompt"]))

    chat_state = resolve_chat_id(payload)
    if chat_state is not None:
        chat = _require_record("chat", Chat, chat_state)
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            return deny

    ai_service: AIPipelineGateway = current_app.extensions["ai_service"]
    try:
        normalized_result = _run(ai_service, payload, prepared, chat_state, resolve_initiated_by(payload))
    except Exception as exc:
        current_app.logger.error("api.ai_interactions.run.failed request_id=%s error=%s", prepared["request_id"], str(exc))
        return jsonify({"error": {"code": "runtime_unavailable", "message": "There was a problem with the model contact the administrator.", "details": {"exception": exc.__class__.__name__}}}), 503

    _warn_if_empty_response(prepared["request_id"], normalized_result)
    persistence_error = persist_interaction(payload=payload, prompt=prepared["prompt"], normalized_result=normalized_result, db_session=db.session, require_record=_require_record)
    if persistence_error is not None:
        current_app.logger.debug("api.ai_interactions.persistence.error request_id=%s chat_id=%s has_error=%s", prepared["request_id"], payload.get("chat_id"), True)
        return persistence_error

    current_app.logger.debug("api.ai_interactions.persistence.end request_id=%s chat_id=%s response_text_len=%s", prepared["request_id"], payload.get("chat_id"), len(normalized_result.get("assistant_text") or ""))
    return jsonify(normalized_result), 200


@api_v1_bp.get("/chats/<int:chat_id>/ai/interactions")
@login_required
def list_chat_ai_interactions(chat_id: int):
    current_app.logger.debug("api.ai_interactions.list.request method=%s path=%s user_id=%s", "GET", f"/api/v1/chats/{chat_id}/ai/interactions", ChatAccessHelper.get_authenticated_user_id())
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    interactions = db.session.query(AIInteraction).filter(AIInteraction.chat_id == chat_id).order_by(AIInteraction.created_at.asc(), AIInteraction.id.asc()).all()
    current_app.logger.debug("api.ai_interactions.list.response chat_id=%s status=%s count=%s", chat_id, 200, len(interactions))
    return jsonify([_serialize_record("ai_interaction", interaction) for interaction in interactions]), 200
