import time

from flask import current_app, jsonify
from flask_login import current_user, login_required

from ...helpers.ai_interaction_helpers import (
    _normalize_interaction_response,
    _persist_ai_interaction,
    _resolve_chat_id,
    _resolve_initiated_by,
    _resolve_provider,
)
from ...helpers.ai_interactions_flow import (
    build_context_and_system_instructions,
    build_prompt_and_messages,
    resolve_model_override,
    run_pipeline,
    compose_system_prompt
)
from .routes import (
    _assert_chat_permissions,
    _publish,
    _require_record,
    _serialize_record,
    _validate_payload,
    api_v1_bp,
    db,
    _read_json_object,
    BadRequestError
)
from ...schemas.validation import AIInteractionPayloadSchema
from ...models import AIInteraction, Chat
from ...services.ai_pipeline.types import AIPipelineRequest
from ...services.chat_access_service import ChatAccessService


@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    """Run a single AI interaction."""
    raw = _read_json_object()
    current_app.logger.debug(
        "api.ai.interactions.payload.raw path=%s json_keys=%s",
        "/api/v1/ai/interactions",
        sorted(raw.keys())
    )
    try:
        payload = _validate_payload(_read_json_object(), AIInteractionPayloadSchema())
    except BadRequestError:
        current_app.logger.debug(
            "api.ai.interactions.payload.validation_failed path=%s json_keys=%s",
            "/api/v1/ai/interactions",
            sorted(raw.keys())
        )
        raise

    print(payload + "prompt not reachign this point")
    user_identity = (
        getattr(current_user, "email", None)
        or getattr(current_user, "id", None)
        or "anonymous"
    )
    current_app.logger.debug(
        "api.ai_interactions.request method=%s path=%s user=%s json_keys=%s",
        "POST",
        "/api/v1/ai/interactions",
        user_identity,
        sorted(payload.keys()),
    )
    prompt, messages = build_prompt_and_messages(payload)
    request_id = str(payload.get("request_id") or "n/a")
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

    context_payload, system_instructions = build_context_and_system_instructions(payload, messages)
    composed_system_prompt = compose_system_prompt(system_instructions, payload)

    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_messages": bool(messages),
            "has_system_prompt": bool(payload.get("system_prompt")),
            "has_guardrail_system_prompt": bool(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT")),
            "has_db_system_instructions": bool(system_instructions),
            "has_rag": bool(payload.get("rag")),
        },
    )

    chat_id = _resolve_chat_id(payload)
    if chat_id is not None:
        chat = _require_record("chat", Chat, chat_id)
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            return deny

    initiated_by = _resolve_initiated_by(payload)
    ai_service = current_app.extensions["ai_service"]
    resolve_model_override(payload, ai_service, context_payload, request_id)

    dto = AIPipelineRequest(
        prompt=prompt,
        messages=messages,
        system_prompt=composed_system_prompt,
        context=context_payload,
        chat_id=chat_id,
        initiated_by=initiated_by,
        class_id=payload.get("class_id"),
        user_id=payload.get("user_id"),
        rag=payload.get("rag") if isinstance(payload.get("rag"), dict) else None,
        request_id=payload.get("request_id"),
    )

    current_app.logger.debug(
        "api.ai_interactions.dto.created request_id=%s provider=%s model=%s prompt_len=%s messages_count=%s has_system_prompt=%s",
        request_id,
        current_app.config.get("AI_PROVIDER"),
        current_app.config.get("AI_MODEL_NAME"),
        len(prompt),
        len(messages),
        bool(dto.system_prompt),
    )
    started_at = time.time()
    result = run_pipeline(ai_service, dto, request_id, prompt)
    if isinstance(result, tuple):
        return result

    current_app.logger.debug(
        "api.ai_interactions.ai_service.run.end request_id=%s provider=%s model=%s response_text_len=%s notes_count=%s response_preview=%r",
        request_id,
        current_app.config.get("AI_PROVIDER"),
        current_app.config.get("AI_MODEL_NAME"),
        len(str((result or {}).get("assistant_text") if isinstance(result, dict) else result or "")),
        len((result or {}).get("notes")) if isinstance(result, dict) and isinstance((result or {}).get("notes"), list) else 0,
        str(result)[:200],
    )
    normalized_result = _normalize_interaction_response(result)
    normalized_result["meta"]["provider"] = _resolve_provider(result)
    current_app.logger.debug(
        "api.ai_interactions.ai_service.run.elapsed request_id=%s duration_ms=%s",
        request_id,
        round((time.time() - started_at) * 1000, 2),
    )
    if not normalized_result.get("assistant_text"):
        current_app.logger.warning(
            "api.ai_interactions.normalize.empty_assistant request_id=%s provider=%s model=%s notes_count=%s",
            request_id,
            normalized_result["meta"].get("provider")
            or current_app.config.get("AI_PROVIDER")
            or "unknown",
            normalized_result["meta"].get("model")
            or current_app.config.get("AI_MODEL_NAME")
            or "unknown",
            len(normalized_result.get("notes") or []),
        )

    persistence_error = _persist_ai_interaction(payload, prompt, normalized_result)
    if persistence_error is not None:
        current_app.logger.debug(
            "api.ai_interactions.persistence.error request_id=%s chat_id=%s has_error=%s",
            request_id,
            payload.get("chat_id"),
            True,
        )
        return persistence_error

    current_app.logger.debug(
        "api.ai_interactions.persistence.end request_id=%s chat_id=%s response_text_len=%s",
        request_id,
        payload.get("chat_id"),
        len(normalized_result.get("assistant_text") or ""),
    )
    return jsonify(normalized_result), 200


@api_v1_bp.get("/chats/<int:chat_id>/ai/interactions")
@login_required
def list_chat_ai_interactions(chat_id: int):
    """List AI interactions for a target chat when visible to the authenticated user."""
    current_app.logger.debug(
        "api.ai_interactions.list.request method=%s path=%s user_id=%s",
        "GET",
        f"/api/v1/chats/{chat_id}/ai/interactions",
        ChatAccessService.get_authenticated_user_id(),
    )
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    interactions = (
        db.session.query(AIInteraction)
        .filter(AIInteraction.chat_id == chat_id)
        .order_by(AIInteraction.created_at.asc(), AIInteraction.id.asc())
        .all()
    )
    current_app.logger.debug(
        "api.ai_interactions.list.response chat_id=%s status=%s count=%s",
        chat_id,
        200,
        len(interactions),
    )
    return jsonify([_serialize_record("ai_interaction", interaction) for interaction in interactions]), 200
