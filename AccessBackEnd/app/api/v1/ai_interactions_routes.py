import time

from flask import current_app, jsonify
from flask_login import login_required

from ...utils.ai_checker import run_pipeline
from ...services.ai_interactions import (
    AIInteractionComponents,
    default_ai_interaction_components,
)
from .routes import (
    _assert_chat_permissions,
    _publish,
    _require_record,
    _serialize_record,
    api_v1_bp,
    db,
)
from ...models import AIInteraction, Chat
from ...utils.chat_access import ChatAccessHelper
from ...services.ai_pipeline.interfaces import AIPipelineServiceInterface


@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    """Run a single AI interaction."""
    components: AIInteractionComponents | None = current_app.extensions.get("ai_interactions_components")
    if components is None:
        components = default_ai_interaction_components()

    payload = components.request_parser.parse_payload()
    built_request = components.request_parser.build_request_dto(payload)
    prompt = built_request.prompt
    messages = built_request.messages
    request_id = built_request.request_id
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

    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_messages": bool(messages),
            "has_system_prompt": bool(payload.get("system_prompt")),
            "has_guardrail_system_prompt": bool(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT")),
            "has_db_system_instructions": bool(built_request.system_instructions),
            "has_rag": bool(payload.get("rag")),
        },
    )

    chat_id = built_request.chat_id
    if chat_id is not None:
        chat = _require_record("chat", Chat, chat_id)
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            return deny

    ai_service: AIPipelineServiceInterface = current_app.extensions["ai_service"]
    preflight_error = components.model_resolver.resolve_runtime_model_selection(
        payload,
        ai_service,
        built_request.context_payload,
        request_id,
    )
    if preflight_error is not None:
        return preflight_error

    dto = built_request.dto

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
    normalized_result = components.response_normalizer.normalize(result)
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

    persistence_error = components.persistence.persist(payload, prompt, normalized_result)
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
        ChatAccessHelper.get_authenticated_user_id(),
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
