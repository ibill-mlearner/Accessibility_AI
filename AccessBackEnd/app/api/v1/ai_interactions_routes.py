from __future__ import annotations

from typing import Any

from flask import current_app, jsonify
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from ...db.repositories.interaction_repo import AIInteractionRepository
from ...models import AIInteraction, AIModel, Chat, UserAccessibilityFeature
from ...models.ai import AccommodationSystemPrompt
from ...schemas.validation import AIInteractionPayloadSchema
from ...services.ai_pipeline_gateway import AIPipelineGateway
from ...utils.ai_checker.mutations import AIInteractionMutations
from ...utils.ai_checker.validators import AIInteractionValidator
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


def _log_payload(raw: dict, payload: dict) -> None:
    current_app.logger.debug(
        "api.ai.interactions.payload.raw path=%s json_keys=%s",
        "/api/v1/ai/interactions",
        sorted(raw.keys()),
    )
    current_app.logger.debug(
        "api.ai.interactions.payload.validated keys=%s",
        sorted(payload.keys()),
    )


def _log_request(payload: dict) -> None:
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


def _derive_selection_from_chat(chat: Chat | None) -> tuple[str, str]:
    _ = chat
    return "", ""


def _resolve_chat_id(payload: dict[str, Any]) -> int | None:
    chat_id = payload.get("chat_id")
    if chat_id is None:
        return None
    return int(chat_id)


def _resolve_initiated_by(payload: dict[str, Any]) -> str:
    if getattr(current_user, "is_authenticated", False):
        return str(current_user.get_id() or getattr(current_user, "email", "authenticated_user"))
    return str(payload.get("user") or payload.get("user_id") or "anonymous")


def _normalize_interaction_response(result: Any) -> dict[str, Any]:
    envelope = AIInteractionMutations.normalize_payload(result)
    normalized = {
        "assistant_text": AIInteractionMutations.strip_prompt_template_echo(envelope.assistant_text),
        "confidence": envelope.confidence,
        "notes": envelope.notes,
        "meta": envelope.meta.copy() if isinstance(envelope.meta, dict) else {},
    }
    if not normalized["assistant_text"]:
        normalized["notes"].append("assistant_empty_after_normalization")
        normalized.setdefault("meta", {}).setdefault("debug", {})["raw_payload_preview"] = AIInteractionMutations.truncate_debug_payload(result)
    return normalized


def _resolve_system_instructions(payload: dict[str, Any]) -> str:
    selected_feature_ids = payload.get("selected_accessibility_link_ids")
    if not isinstance(selected_feature_ids, list) or not selected_feature_ids:
        return ""

    normalized_ids: list[int] = []
    for feature_id in selected_feature_ids:
        try:
            normalized_ids.append(int(feature_id))
        except (TypeError, ValueError):
            continue

    rows = (
        db.session.query(UserAccessibilityFeature)
        .filter(UserAccessibilityFeature.accommodation_id.in_(normalized_ids))
        .order_by(UserAccessibilityFeature.accommodation_id.asc())
        .all()
    )
    return "\n\n".join(
        AIInteractionValidator.to_clean_text(row.accommodation.details)
        for row in rows
        if row.accommodation and row.accommodation.details
    )


def _prepare_interaction_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    raw_messages = payload.get("messages")
    messages = raw_messages if isinstance(raw_messages, list) else []

    if not prompt:
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "").lower() != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                prompt = content.strip()
                break

    guardrail = str(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT") or "").strip()
    request_system_prompt = str(payload.get("system_prompt") or "").strip()
    system_instructions = _resolve_system_instructions(payload)
    system_prompt = "\n\n".join(part for part in [guardrail, system_instructions, request_system_prompt] if part) or None

    context_payload = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    if messages and "messages" not in context_payload:
        context_payload["messages"] = messages
    context_payload["runtime_model_selection"] = {
        "provider": payload.get("provider") or current_app.config.get("AI_PROVIDER"),
        "model_id": payload.get("model_id") or current_app.config.get("AI_MODEL_NAME"),
        "source": "request_or_config",
    }

    return {
        "prompt": prompt,
        "messages": messages,
        "context_payload": context_payload,
        "system_prompt": system_prompt,
        "request_id": str(payload.get("request_id") or "n/a"),
    }


def _resolve_ai_model_id(result: Any) -> int:
    meta = result.get("meta") if isinstance(result, dict) else {}
    provider = AIInteractionValidator.to_clean_text(
        (meta or {}).get("provider") or current_app.config.get("AI_PROVIDER") or "huggingface",
        lower=True,
    ) or "huggingface"
    model_name = AIInteractionValidator.to_clean_text(
        (meta or {}).get("model_id")
        or (meta or {}).get("model")
        or (result.get("model_id") if isinstance(result, dict) else None)
        or (result.get("model") if isinstance(result, dict) else None)
        or current_app.config.get("AI_MODEL_NAME")
        or "",
    ) or f"{provider}-default"

    model = db.session.query(AIModel).filter(AIModel.provider == provider, AIModel.model_id == model_name).first()
    if model is None:
        model = AIModel(provider=provider, model_id=model_name, active=True)
        db.session.add(model)
        db.session.flush()
    else:
        model.active = True
    return int(model.id)


def _persist_interaction(payload: dict[str, Any], prompt: str, result: dict[str, Any]) -> tuple[Any, int] | None:
    try:
        chat_id = _resolve_chat_id(payload)
        prompt_link_id = payload.get("accommodations_id_system_prompts_id")
        if prompt_link_id is not None:
            prompt_link_id = int(prompt_link_id)
            _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)

        interaction = AIInteractionRepository(AIInteraction).create(
            db.session,
            prompt=prompt,
            response_text=result.get("assistant_text") or "",
            chat_id=chat_id,
            ai_model_id=_resolve_ai_model_id(result),
            accommodations_id_system_prompts_id=prompt_link_id,
        )

        if chat_id is not None:
            chat = _require_record("chat", Chat, chat_id)
            chat.ai_interaction_id = interaction.id

        db.session.commit()
        return None
    except (TypeError, ValueError, SQLAlchemyError) as exc:
        db.session.rollback()
        code = "persistence_error" if isinstance(exc, SQLAlchemyError) else "bad_request"
        status = 500 if isinstance(exc, SQLAlchemyError) else 400
        return jsonify({"error": {"code": code, "message": "Failed to persist AI interaction", "details": {"exception": exc.__class__.__name__}}}), status


def _run(
    ai_service: AIPipelineGateway,
    payload: dict,
    prepared: dict,
    chat_id: int | None,
    initiated_by: str,
):
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
    return _normalize_interaction_response(result)


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
    prepared = _prepare_interaction_inputs(payload)
    _log_interaction_start(payload, prepared["request_id"], prepared["prompt"])
    _publish_request_summary(prepared["prompt"], prepared["messages"], payload, prepared["system_prompt"], bool(prepared["system_prompt"]))

    chat_state = _resolve_chat_id(payload)
    if chat_state is not None:
        chat = _require_record("chat", Chat, chat_state)
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            return deny

    ai_service: AIPipelineGateway = current_app.extensions["ai_service"]

    try:
        normalized_result = _run(
            ai_service,
            payload,
            prepared,
            chat_state,
            _resolve_initiated_by(payload),
        )
    except Exception as exc:
        current_app.logger.error("api.ai_interactions.run.failed request_id=%s error=%s", prepared["request_id"], str(exc))
        return (
            jsonify(
                {
                    "error": {
                        "code": "runtime_unavailable",
                        "message": "There was a problem with the model contact the administrator.",
                        "details": {"exception": exc.__class__.__name__},
                    }
                }
            ),
            503,
        )

    _warn_if_empty_response(prepared["request_id"], normalized_result)
    persistence_error = _persist_interaction(payload, prepared["prompt"], normalized_result)
    if persistence_error is not None:
        current_app.logger.debug(
            "api.ai_interactions.persistence.error request_id=%s chat_id=%s has_error=%s",
            prepared["request_id"],
            payload.get("chat_id"),
            True,
        )
        return persistence_error

    current_app.logger.debug(
        "api.ai_interactions.persistence.end request_id=%s chat_id=%s response_text_len=%s",
        prepared["request_id"],
        payload.get("chat_id"),
        len(normalized_result.get("assistant_text") or ""),
    )
    return jsonify(normalized_result), 200


@api_v1_bp.get("/chats/<int:chat_id>/ai/interactions")
@login_required
def list_chat_ai_interactions(chat_id: int):
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
