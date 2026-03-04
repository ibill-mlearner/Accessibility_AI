import time

from typing import Any
from flask import current_app, jsonify, session
from flask_login import current_user, login_required

from .routes import (
    _apply_field_updates,
    _assert_chat_permissions,
    _publish,
    _require_record,
    _serialize_record,
    api_v1_bp,
    db,
    _read_json_object,
    _parse_int_field,
    _validate_payload,
    BadRequestError
)

from ...services.chat_access_service import ChatAccessService
from ...services.ai_pipeline.exceptions import AIPipelineUpstreamError
from ...services.ai_pipeline.model_catelog import MODEL_FAMILIES, family_id_from_model_id
from ...services.ai_pipeline.types import AIPipelineRequest
from ...models import AIInteraction, Chat, CourseClass, SystemPrompt, User
from .helpers.ai_interaction_helpers import (
    _extract_available_model_ids,
    _normalize_interaction_response,
    _persist_ai_interaction,
    _resolve_chat_id,
    _resolve_initiated_by,
    _resolve_provider,
    _resolve_selected_model,
    _resolve_system_instructions,
    resolve_model_selection,
)
from .schemas.validation import AIInteractionPayloadSchema

@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    """Run a single AI interaction."""
    payload = _validate_payload(_read_json_object(), AIInteractionPayloadSchema())
    user_identity = getattr(current_user, "email", None) or getattr(current_user, "id", None) or "anonymous"
    current_app.logger.debug(
        "api.ai_interactions.request method=%s path=%s user=%s json_keys=%s",
        "POST",
        "/api/v1/ai/interactions",
        user_identity,
        sorted(payload.keys()),
    )
    prompt = (payload.get("prompt") or "").strip()
    request_id = str(payload.get("request_id") or "n/a")
    current_app.logger.debug(
        "api.ai_interactions.create.start request_id=%s provider=%s model=%s timeout_seconds=%s prompt_len=%s messages_count=%s prompt_preview=%r",
        request_id,
        current_app.config.get("AI_PROVIDER"),
        current_app.config.get("AI_MODEL_NAME"),
        current_app.config.get("AI_TIMEOUT_SECONDS"),
        len(prompt),
        len(payload.get("messages")) if isinstance(payload.get("messages"), list) else 0,
        prompt[:200]
    )

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

    system_instructions = _resolve_system_instructions(payload)

    context_payload = payload.get("context")
    if not isinstance(context_payload, dict):
        context_payload = {}
    if messages and "messages" not in context_payload:
        context_payload["messages"] = messages


    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_messages": bool(messages),
            "has_system_prompt": bool(payload.get("system_prompt")),
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

    # `ai_service` is registered during app startup in `app/__init__.py` via
    # `build_ai_service(...)`, which constructs `AIPipelineService` from
    # `app.services.ai_pipeline` and stores it at `app.extensions["ai_service"]`.
    #
    # Logging bootstrap may wrap that pipeline service in
    # `InteractionLoggingService`, but `run_interaction(...)` still delegates to
    # the same underlying `AIPipelineService` implementation.
    ai_service = current_app.extensions["ai_service"]
    dto = AIPipelineRequest(
        prompt=prompt,
        messages=messages,
        system_prompt=system_instructions or (payload.get("system_prompt") or None),
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
        bool(dto.system_prompt)
    )
    started_at = time.time()
    try:
        result = ai_service.run(dto)
    except AIPipelineUpstreamError as exc:
        current_app.logger.warning(
            "api.ai_interactions.ai_service.run.error request_id=%s provider=%s model=%s upstream_source=%s error_type=%s prompt_preview=%r",
            request_id,
            current_app.config.get("AI_PROVIDER"),
            current_app.config.get("AI_MODEL_NAME"),
            (exc.details or {}).get("source", "unknown"),
            exc.__class__.__name__,
            prompt[:200]
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
            normalized_result["meta"].get("provider") or current_app.config.get("AI_PROVIDER") or "unknown",
            normalized_result["meta"].get("model") or current_app.config.get("AI_MODEL_NAME") or "unknown",
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

@api_v1_bp.get("/ai/models/available")
@login_required
def list_available_ai_models():
    """Return read-only inventory of currently discoverable AI models."""
    ai_service = current_app.extensions["ai_service"]
    payload = ai_service.list_available_models()
    return jsonify(payload), 200


@api_v1_bp.get("/ai/catalog")
@login_required
def get_ai_catalog():
    """Return catalog grouped by model family with discoverability and current selection."""
    ai_service = current_app.extensions["ai_service"]
    inventory = ai_service.list_available_models()
    available_by_provider = _extract_available_model_ids(inventory)

    families: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        models: list[dict[str, Any]] = []
        for provider, candidates in family.provider_candidates.items():
            for model_id in candidates:
                models.append(
                    {
                        "provider": provider,
                        "model_id": model_id,
                        "available": model_id.lower() in available_by_provider.get(provider, set()),
                    }
                )
        families.append(
            {
                "family_id": family.family_id,
                "label": family.label,
                "owner": family.owner,
                "models": models,
            }
        )

    response_payload = {
        "families": families,
        "selected": _resolve_selected_model(inventory),
    }
    return jsonify(response_payload), 200

@api_v1_bp.post('/ai/selection')
@login_required
def set_ai_selection():
    """Persist per-session AI model selection for the authenticated user."""
    payload = _read_json_object()
    ai_service = current_app.extensions["ai_service"]
    inventory = ai_service.list_available_models()
    available_by_provider = _extract_available_model_ids(inventory)

    has_provider_pair = bool(payload.get("provider") and payload.get("model_id"))
    has_family_pair = bool(payload.get("family_id") and payload.get("provider_preference"))
    if has_provider_pair == has_family_pair:
        raise BadRequestError(
            "Provide either provider/model_id or family_id/provider_preference",
        )

    try:
        if has_provider_pair:
            selected = resolve_model_selection(
                provider=str(payload.get("provider") or "").strip().lower(),
                model_id=str(payload.get("model_id") or "").strip(),
                available_model_ids=available_by_provider,
            )
        else:
            selected = resolve_model_selection(
                family_id=str(payload.get("family_id") or "").strip(),
                provider_preference=str(payload.get("provider_preference") or "").strip().lower(),
                available_model_ids=available_by_provider,
            )
    except ValueError as exc:
        err_msg = str(exc)
        if "No candidate model available" in err_msg:
            return jsonify({"error": "no available model for requested family"}), 400
        raise BadRequestError(err_msg) from exc

    session["ai_model_selection"] = {
        "user_id": int(current_user.id),
        "auth_session_id": session.get("auth_session_id"),
        "provider": selected["provider"],
        "model_id": selected["model_id"],
    }

    return jsonify(
        {
            "provider": selected["provider"],
            "model_id": selected["model_id"],
            "family_id": family_id_from_model_id(selected["model_id"]),
        }
    ), 200

@api_v1_bp.get("/system-prompts")
@login_required
def list_system_prompts():
    prompts = db.session.query(SystemPrompt).order_by(SystemPrompt.id.asc()).all()
    return jsonify([_serialize_record("system_prompt", prompt) for prompt in prompts]), 200


@api_v1_bp.post("/system-prompts")
@login_required
def create_system_prompt():
    payload = _read_json_object()

    #todo: Restrict writes to instructor/admin roles and class ownership.
    class_id = _parse_int_field(payload.get("class_id"), field_name="class_id")
    instructor_id = _parse_int_field(payload.get("instructor_id"), field_name="instructor_id")
    text = str(payload.get("text") or "").strip()
    if not text:
        raise BadRequestError("text is required")

    if class_id is not None:
        _require_record("class", CourseClass, class_id)
    if instructor_id is not None:
        _require_record("user", User, instructor_id)

    prompt = SystemPrompt(class_id=class_id, instructor_id=instructor_id, text=text)
    db.session.add(prompt)
    db.session.commit()
    return jsonify(_serialize_record("system_prompt", prompt)), 201


@api_v1_bp.get("/system-prompts/<int:prompt_id>")
@login_required
def get_system_prompt(prompt_id: int):
    prompt = _require_record("system_prompt", SystemPrompt, prompt_id)
    return jsonify(_serialize_record("system_prompt", prompt)), 200


@api_v1_bp.patch("/system-prompts/<int:prompt_id>")
@login_required
def update_system_prompt(prompt_id: int):
    prompt = _require_record("system_prompt", SystemPrompt, prompt_id)
    payload = _read_json_object()

    #todo: Restrict writes to instructor/admin roles and class ownership.
    if "class_id" in payload:
        class_id = _parse_int_field(payload.get("class_id"), field_name="class_id")
        if class_id is not None:
            _require_record("class", CourseClass, class_id)
        payload['class_id'] = class_id

    if "instructor_id" in payload:
        instructor_id = _parse_int_field(payload.get("instructor_id"), field_name="instructor_id")
        if instructor_id is not None:
            _require_record("user", User, instructor_id)
        ppayload['instructor_id'] = instructor_id

    _apply_field_updates(
        prompt,
        payload,
        (
            'class_id',
            'instuctor_id'
        )
    )

    if "text" in payload:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise BadRequestError("text is required")
        prompt.text = text

    db.session.commit()
    return jsonify(_serialize_record("system_prompt", prompt)), 200


@api_v1_bp.delete("/system-prompts/<int:prompt_id>")
@login_required
def delete_system_prompt(prompt_id: int):
    prompt = _require_record("system_prompt", SystemPrompt, prompt_id)

    #todo: Restrict writes to instructor/admin roles and class ownership.
    response_payload = _serialize_record("system_prompt", prompt)
    db.session.delete(prompt)
    db.session.commit()
    return jsonify(response_payload), 200
