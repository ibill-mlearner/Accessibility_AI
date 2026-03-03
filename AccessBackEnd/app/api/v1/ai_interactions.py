import json

from typing import Any
from flask import current_app, jsonify
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from .routes import (
    _apply_field_updates,
    _assert_chat_permissions,
    _forbidden_response,
    _publish,
    _require_record,
    _serialize_record,
    api_v1_bp,
    db,
    _raise_bad_request_from_exception,
    _read_json_object,
    _parse_int_field,
    _validate_payload,
    BadRequestError
)

from ...services.chat_access_service import ChatAccessService
from ...services.ai_pipeline.exceptions import AIPipelineUpstreamError
from ...services.ai_pipeline.types import AIPipelineRequest
from ...models import AIModel, AIInteraction, Chat, CourseClass, SystemPrompt, User
from ...models.ai_interaction import AccommodationSystemPrompt
from ...db.repositories.interaction_repo import AIInteractionRepository
from .schemas.validation import AIInteractionPayloadSchema

def _extract_response_text(result: Any) -> str:
    """Normalize provider payload into a storable interaction response string."""
    normalized = _normalize_interaction_response(result)
    return normalized["assistant_text"]


def _truncate_debug_payload(value: Any, *, limit: int = 1200) -> str:
    """Safely serialize payload snippets for metadata without exposing oversized blobs."""
    serialized = value if isinstance(value, str) else json.dumps(value, default=str)
    return serialized if len(serialized) <= limit else f"{serialized[:limit]}… [truncated]"


def _strip_prompt_template_echo(text: str) -> str:
    """Drop obvious prompt-template scaffolding from assistant output fields."""
    template_tokens = ("{prompt}", "{context}", "{question}", "{{", "}}")
    cleaned_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not any(token in line.lower() for token in template_tokens)
    ]
    cleaned = "\n".join(cleaned_lines).strip()
    return cleaned.removeprefix("Answer:").strip()


def _normalize_interaction_response(result: Any) -> dict[str, Any]:
    """Normalize provider payload into canonical UI response shape."""
    normalized_response: dict[str, Any] = {
        "assistant_text": "",
        "confidence": None,
        "notes": [],
        "meta": {},
    }

    if isinstance(result, dict):
        candidate = next(
            (result.get(key) for key in ("assistant_text", "result", "answer", "response_text", "response", "output", "text") if result.get(key) is not None),
            "",
        )
        normalized_response["assistant_text"] = _strip_prompt_template_echo(str(candidate))

        confidence = result.get("confidence")
        normalized_response["confidence"] = float(confidence) if isinstance(confidence, (int, float)) else None

        notes = result.get("notes")
        if isinstance(notes, list):
            normalized_response["notes"] = [str(note) for note in notes]
        elif isinstance(notes, str) and notes.strip():
            normalized_response["notes"] = [notes.strip()]

        meta_payload = result.get("meta")
        normalized_response["meta"] = meta_payload.copy() if isinstance(meta_payload, dict) else {}
    else:
        normalized_response["assistant_text"] = _strip_prompt_template_echo(str(result or ""))

    # Keep raw provider payload only in debug metadata for investigation.
    if not normalized_response["assistant_text"]:
        normalized_response["notes"].append("Assistant response was empty after normalization.")
        normalized_response["meta"].setdefault("debug", {})["raw_payload_preview"] = _truncate_debug_payload(result)

    return normalized_response


def _resolve_initiated_by(payload: dict[str, Any]) -> str:
    """Resolve actor identifier used for AI interaction auditing."""
    if getattr(current_user, "is_authenticated", False):
        return str(
            current_user.get_id()
            or getattr(current_user, "email", "authenticated_user")
        )
    if payload.get("user"):
        return str(payload["user"])
    if payload.get("user_id"):
        return str(payload["user_id"])
    return "anonymous"

def _resolve_system_instructions(payload: dict[str, Any]) -> str:
    """Resolve DB backed system instructions for AI providers"""

    prompt_link_id = _resolve_prompt_link_id(payload)
    if prompt_link_id is None:
        return ""
    
    prompt_link = _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)
    parts = [
        (prompt_link.system_prompt.text or "").strip() if prompt_link.system_prompt else "",
        (prompt_link.accommodation.details or "").strip() if prompt_link.accommodation else ""
    ]

    return "\n\n".join(p for p in parts if p)

def _resolve_provider(result: Any) -> str:
    """Resolve persisted provider name from response payload or app config."""
    provider = current_app.config.get("AI_PROVIDER") or "unknown"
    if isinstance(result, dict):
        meta_payload = result.get("meta")
        if isinstance(meta_payload, dict) and meta_payload.get("provider"):
            return str(meta_payload["provider"])
        if result.get("provider"):
            return str(result["provider"])
    return str(provider)


def _resolve_ai_model_id(result: Any) -> int:
    provider_name = _resolve_provider(result)
    model = db.session.query(AIModel).filter(AIModel.provider == provider_name).first()
    if model is None:
        model = AIModel(provider=provider_name, active=True)
        db.session.add(model)
        db.session.flush()
    return int(model.id)


def _resolve_prompt_link_id(payload: dict[str, Any]) -> int | None:
    selected_link_ids = payload.get("selected_accommodations_id_system_prompts_ids")
    if isinstance(selected_link_ids, list):
        for candidate in selected_link_ids:
            try:
                resolved_id = int(candidate)
            except (TypeError, ValueError):
                continue
            prompt_link = (
                db.session.query(AccommodationSystemPrompt.id)
                .filter(AccommodationSystemPrompt.id == resolved_id)
                .first()
            )
            if prompt_link is not None:
                return resolved_id
    link_id = payload.get("accommodations_id_system_prompts_id")
    if link_id is None:
        return None
    try:
        return int(link_id)
    except (TypeError, ValueError) as exc:
        _raise_bad_request_from_exception(exc, message="accommodations_id_system_prompts_id must be an integer")


def _resolve_chat_id(payload: dict[str, Any]) -> int | None:
    """Extract optional chat id and validate integer shape when present."""
    chat_id = payload.get("chat_id")
    if chat_id is None:
        return None
    try:
        return int(chat_id)
    except (TypeError, ValueError) as exc:
        _raise_bad_request_from_exception(
            exc,
            message="chat_id must be an integer",
        )

def _build_interaction_persistence_payload(payload: dict[str, Any], result: Any) -> dict[str, int | None]:
    """Resolve and validate FK inputs needed for interaction persistence."""
    chat_id = _resolve_chat_id(payload)
    prompt_link_id = _resolve_prompt_link_id(payload)
    if prompt_link_id is not None:
        _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)

    return {
        "chat_id": chat_id,
        "prompt_link_id": prompt_link_id,
        "model_id": _resolve_ai_model_id(result),
    }

def _sync_chat_latest_interaction(chat_id: int | None, interaction_id: int) -> None:
    """Attach latest AI interaction id onto the chat when chat linkage exists."""
    if chat_id is None:
        return

    chat = _require_record("chat", Chat, chat_id)
    chat.ai_interaction_id = interaction_id

def _persist_ai_interaction(
    payload: dict[str, Any], prompt: str, result: Any
) -> tuple[Any, int] | None:
    """Persist an AI interaction; return error response tuple when persistence fails."""
    interaction_repo = AIInteractionRepository(AIInteraction)

    try:
        normalized = _normalize_interaction_response(result)
        persistence_ids = _build_interaction_persistence_payload(payload, result)

        interaction = interaction_repo.create(
            db.session,
            prompt=prompt,
            response_text=normalized["assistant_text"],
            chat_id=persistence_ids["chat_id"],
            ai_model_id=persistence_ids["model_id"],
            accommodations_id_system_prompts_id=persistence_ids["prompt_link_id"],
        )
        _sync_chat_latest_interaction(persistence_ids["chat_id"], interaction.id)

        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": {
                        "code": "persistence_error",
                        "message": "Failed to persist AI interaction",
                        "details": {"exception": exc.__class__.__name__},
                    }
                }
            ),
            500,
        )

    return None

@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    """Run a single AI interaction."""
    payload = _validate_payload(_read_json_object(), AIInteractionPayloadSchema())

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

    try:
        result = ai_service.run(dto)
    except AIPipelineUpstreamError as exc:
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
    normalized_result = _normalize_interaction_response(result)
    normalized_result["meta"]["provider"] = _resolve_provider(result)

    persistence_error = _persist_ai_interaction(payload, prompt, normalized_result)
    if persistence_error is not None:
        return persistence_error

    return jsonify(normalized_result), 200

@api_v1_bp.get("/chats/<int:chat_id>/ai/interactions")
@login_required
def list_chat_ai_interactions(chat_id: int):
    """List AI interactions for a target chat when visible to the authenticated user."""
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
    return jsonify([_serialize_record("ai_interaction", interaction) for interaction in interactions]), 200

@api_v1_bp.get("/ai/models/available")
@login_required
def list_available_ai_models():
    """Return read-only inventory of currently discoverable AI models."""
    ai_service = current_app.extensions["ai_service"]
    payload = ai_service.list_available_models()
    return jsonify(payload), 200

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
