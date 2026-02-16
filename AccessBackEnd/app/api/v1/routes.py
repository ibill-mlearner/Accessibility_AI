from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user
from sqlalchemy.exc import SQLAlchemyError

from ..errors import BadRequestError, NotFoundError
from .api_view import register_api_view_route

from ...db.repositories.interaction_repo import AIInteractionRepository
from ...extensions import db
from ...models import AIInteraction, Chat, Message, User
from ...services.logging import DomainEvent

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

_RESOURCE_API_TO_MODEL_FIELDS: dict[str, dict[str, str]] = {
    "chat": {
        "class": "class_id",
        "class_id": "class_id",
        "user": "user_id",
        "user_id": "user_id",
        "start": "started_at",
        "started_at": "started_at",
        "title": "title",
        "model": "model",
    },
    "message": {
        "chat": "chat_id",
        "chat_id": "chat_id",
        "text": "message_text",
        "message_text": "message_text",
        "vote": "vote",
        "note": "note",
        "help_intent": "help_intent",
    },
}


def _deserialize_payload(resource: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Map API payload keys onto model field names for CRUD operations."""
    field_map = _RESOURCE_API_TO_MODEL_FIELDS.get(resource, {})
    return {field_map.get(key, key): value for key, value in payload.items()}


def _serialize_record(resource: str, record: Any) -> dict[str, Any]:
    """Serialize ORM objects using API field names for stable endpoint envelopes."""
    if resource == "chat":
        return {
            "id": record.id,
            "class_id": record.class_id,
            "user_id": record.user_id,
            "title": record.title,
            "model": record.model,
            "started_at": record.started_at.isoformat() if record.started_at else None,
        }

    if resource == "message":
        return {
            "id": record.id,
            "chat_id": record.chat_id,
            "message_text": record.message_text,
            "vote": record.vote,
            "note": record.note,
            "help_intent": record.help_intent,
        }

    return {}


def _publish(event_name: str, payload: dict[str, Any] | None = None) -> None:
    """Publish a domain event for endpoint observability."""
    current_app.extensions["event_bus"].publish(DomainEvent(event_name, payload or {}))


def _read_json_object() -> dict[str, Any]:
    """Read request JSON body and require object payloads for route stubs."""
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequestError("json body required")
    if not isinstance(payload, dict):
        raise BadRequestError("json object body required")
    return payload


def _todo_response(
    *,
    endpoint: str,
    next_steps: list[str],
    payload: dict[str, Any] | None = None,
    status_code: int = 501,
):
    """Return explicit placeholder output for handlers that are intentionally unimplemented."""
    return (
        jsonify(
            {
                "message": "TODO: implement",
                "endpoint": endpoint,
                "next_steps": next_steps,
                "payload": payload or {},
            }
        ),
        status_code,
    )


@api_v1_bp.post("/auth/register")
def register_auth_user():
    """Create and authenticate a user account for API-v1 clients."""
    payload = _read_json_object()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "student").strip().lower()

    if not email or not password:
        raise BadRequestError("email and password are required")

    if db.session.query(User).filter_by(normalized_email=email).first() is not None:
        return (
            jsonify(
                {
                    "error": {
                        "code": "conflict",
                        "message": "email already registered",
                        "details": {},
                    }
                }
            ),
            409,
        )

    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    user.mark_login_success()
    login_user(user)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "registration successful",
                "user": {"id": user.id, "email": user.email, "role": user.role},
            }
        ),
        201,
    )


@api_v1_bp.post("/auth/login")
def login_auth_user():
    """Authenticate an API-v1 user and establish a login session."""
    payload = _read_json_object()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        raise BadRequestError("email and password are required")

    user = db.session.query(User).filter_by(normalized_email=email).first()
    if user is None or not user.check_password(password):
        return (
            jsonify(
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "invalid credentials",
                        "details": {},
                    }
                }
            ),
            401,
        )

    user.mark_login_success()
    login_user(user)
    db.session.commit()

    return jsonify({"message": "login successful", "user": {"id": user.id, "email": user.email}}), 200


@api_v1_bp.get("/chats")
@login_required
def list_chats():
    """List chats for the authenticated user in a stable collection envelope."""
    user_id = int(current_user.get_id())
    chats = (
        db.session.query(Chat)
        .filter(Chat.user_id == user_id)
        .order_by(Chat.started_at.desc(), Chat.id.desc())
        .all()
    )
    return jsonify({"items": [_serialize_record("chat", chat) for chat in chats], "next_cursor": None}), 200


@api_v1_bp.post("/chats")
@login_required
def create_chat():
    """Create a chat for the authenticated user in a class context."""
    payload = _deserialize_payload("chat", _read_json_object())
    authenticated_user_id = int(current_user.get_id())

    class_id = payload.get("class_id")
    if class_id is None:
        raise BadRequestError("class_id is required")

    requested_user_id = int(payload.get("user_id", authenticated_user_id))
    if requested_user_id != authenticated_user_id:
        return (
            jsonify(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "cannot create chats for another user",
                        "details": {},
                    }
                }
            ),
            403,
        )

    chat = Chat(
        class_id=int(class_id),
        user_id=authenticated_user_id,
        title=(payload.get("title") or "New Chat").strip(),
        model=(payload.get("model") or current_app.config.get("AI_MODEL_NAME") or "unknown").strip(),
    )
    db.session.add(chat)
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 201


@api_v1_bp.get("/chats/<int:chat_id>/messages")
@login_required
def list_chat_messages(chat_id: int):
    """List messages for a target chat when visible to the authenticated user."""
    chat = db.session.get(Chat, chat_id)
    if chat is None:
        raise NotFoundError("chat not found")
    if chat.user_id != int(current_user.get_id()):
        return (
            jsonify(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "user is not authorized for this chat",
                        "details": {},
                    }
                }
            ),
            403,
        )

    messages = (
        db.session.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.id.asc())
        .all()
    )
    return (
        jsonify(
            {
                "chat_id": chat_id,
                "items": [_serialize_record("message", message) for message in messages],
                "next_cursor": None,
            }
        ),
        200,
    )


@api_v1_bp.post("/chats/<int:chat_id>/messages")
@login_required
def create_chat_message(chat_id: int):
    """Create a message on a target chat when writable by the current user."""
    chat = db.session.get(Chat, chat_id)
    if chat is None:
        raise NotFoundError("chat not found")
    if chat.user_id != int(current_user.get_id()):
        return (
            jsonify(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "user is not authorized for this chat",
                        "details": {},
                    }
                }
            ),
            403,
        )

    payload = _deserialize_payload("message", _read_json_object())
    message_text = (payload.get("message_text") or "").strip()
    help_intent = (payload.get("help_intent") or "").strip()

    if not message_text:
        raise BadRequestError("message_text is required")
    if not help_intent:
        raise BadRequestError("help_intent is required")

    message = Message(
        chat_id=chat_id,
        message_text=message_text,
        vote=(payload.get("vote") or "good").strip(),
        note=(payload.get("note") or "no").strip(),
        help_intent=help_intent,
    )
    db.session.add(message)
    db.session.commit()
    return jsonify(_serialize_record("message", message)), 201


@api_v1_bp.get("/health")
@login_required
def health():
    """Service heartbeat endpoint for deployment/readiness checks."""
    _publish("api.health_checked")
    return jsonify(
        {"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")}
    )


def _extract_response_text(result: Any) -> str:
    """Normalize provider payload into a storable interaction response string."""
    if isinstance(result, dict):
        for key in ("response_text", "response", "answer", "result"):
            value = result.get(key)
            if value is not None:
                return str(value)

        if "data" in result:
            data_value = result["data"]
            if isinstance(data_value, str):
                return data_value
            if data_value is not None:
                return json.dumps(data_value, default=str)

    if isinstance(result, str):
        return result

    return json.dumps(result, default=str)


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


def _resolve_chat_id(payload: dict[str, Any]) -> int | None:
    """Extract optional chat id and validate integer shape when present."""
    chat_id = payload.get("chat_id")
    if chat_id is None:
        return None
    try:
        return int(chat_id)
    except (TypeError, ValueError) as exc:
        raise BadRequestError("chat_id must be an integer") from exc


def _persist_ai_interaction(
    payload: dict[str, Any], prompt: str, result: Any
) -> tuple[Any, int] | None:
    """Persist an AI interaction; return error response tuple when persistence fails."""
    interaction_repo = AIInteractionRepository(AIInteraction)

    try:
        interaction_repo.create(
            db.session,
            prompt=prompt,
            response_text=_extract_response_text(result),
            provider=_resolve_provider(result),
            chat_id=_resolve_chat_id(payload),
        )
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
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt") or ""

    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_system_prompt": bool(payload.get("system_prompt")),
            "has_rag": bool(payload.get("rag")),
        },
    )

    initiated_by = _resolve_initiated_by(payload)

    try:
        result = current_app.extensions["ai_service"].run_interaction(
            prompt=prompt,
            context=payload.get("context"),
            initiated_by=initiated_by,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        return (
            jsonify(
                {
                    "error": {
                        "code": "upstream_error",
                        "message": str(exc),
                        "details": {},
                    }
                }
            ),
            502,
        )

    persistence_error = _persist_ai_interaction(payload, prompt, result)
    if persistence_error is not None:
        return persistence_error

    return jsonify(result), 200


register_api_view_route(api_v1_bp)
