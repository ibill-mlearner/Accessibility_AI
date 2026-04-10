from __future__ import annotations

from typing import Any

from flask import current_app, jsonify
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from ..db.repositories.interaction_repo import AIInteractionRepository
from ..models import AIInteraction, AIModel, Chat, UserAccessibilityFeature
from ..models.ai import AccommodationSystemPrompt
from .ai_checker.mutations import AIInteractionMutations
from .ai_checker.validators import AIInteractionValidator


def derive_selection_from_chat(chat: Chat | None) -> tuple[str, str]:
    _ = chat
    return "", ""


def resolve_chat_id(payload: dict[str, Any]) -> int | None:
    chat_id = payload.get("chat_id")
    if chat_id is None:
        return None
    return int(chat_id)


def resolve_initiated_by(payload: dict[str, Any]) -> str:
    if getattr(current_user, "is_authenticated", False):
        return str(current_user.get_id() or getattr(current_user, "email", "authenticated_user"))
    return str(payload.get("user") or payload.get("user_id") or "anonymous")


def normalize_interaction_response(result: Any) -> dict[str, Any]:
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


def resolve_system_instructions(payload: dict[str, Any], *, db_session: Any) -> str:
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
        db_session.query(UserAccessibilityFeature)
        .filter(UserAccessibilityFeature.accommodation_id.in_(normalized_ids))
        .order_by(UserAccessibilityFeature.accommodation_id.asc())
        .all()
    )
    return "\n\n".join(
        AIInteractionValidator.to_clean_text(row.accommodation.details)
        for row in rows
        if row.accommodation and row.accommodation.details
    )


def prepare_interaction_inputs(payload: dict[str, Any], *, db_session: Any) -> dict[str, Any]:
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
    system_instructions = resolve_system_instructions(payload, db_session=db_session)
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


def resolve_ai_model_id(result: Any, *, db_session: Any) -> int:
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

    model = db_session.query(AIModel).filter(AIModel.provider == provider, AIModel.model_id == model_name).first()
    if model is None:
        model = AIModel(provider=provider, model_id=model_name, active=True)
        db_session.add(model)
        db_session.flush()
    else:
        model.active = True
    return int(model.id)


def persist_interaction(
    *,
    payload: dict[str, Any],
    prompt: str,
    normalized_result: dict[str, Any],
    db_session: Any,
    require_record: Any,
) -> tuple[Any, int] | None:
    try:
        chat_id = resolve_chat_id(payload)
        prompt_link_id = payload.get("accommodations_id_system_prompts_id")
        if prompt_link_id is not None:
            prompt_link_id = int(prompt_link_id)
            require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)

        interaction = AIInteractionRepository(AIInteraction).create(
            db_session,
            prompt=prompt,
            response_text=normalized_result.get("assistant_text") or "",
            chat_id=chat_id,
            ai_model_id=resolve_ai_model_id(normalized_result, db_session=db_session),
            accommodations_id_system_prompts_id=prompt_link_id,
        )

        if chat_id is not None:
            chat = require_record("chat", Chat, chat_id)
            chat.ai_interaction_id = interaction.id

        db_session.commit()
        return None
    except (TypeError, ValueError, SQLAlchemyError) as exc:
        db_session.rollback()
        code = "persistence_error" if isinstance(exc, SQLAlchemyError) else "bad_request"
        status = 500 if isinstance(exc, SQLAlchemyError) else 400
        return jsonify({"error": {"code": code, "message": "Failed to persist AI interaction", "details": {"exception": exc.__class__.__name__}}}), status
