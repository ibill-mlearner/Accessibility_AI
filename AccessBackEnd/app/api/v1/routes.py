from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from ..errors import BadRequestError, NotFoundError
from .api_view import register_api_view_route

from ...db.repositories.interaction_repo import AIInteractionRepository
from ...extensions import db
from ...models import AIInteraction, Chat, CourseClass, Feature, Message, Note, User, UserClassEnrollment
from ...models.identity_defaults import build_transitional_identity_defaults
from ...services.chat_access_service import ChatAccessService
from ...services.ai_pipeline import AIPipelineUpstreamError
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
    "note": {
        "class": "class_id",
        "class_id": "class_id",
        "chat": "chat_id",
        "chat_id": "chat_id",
        "date": "noted_on",
        "noted_on": "noted_on",
        "content": "content",
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
            "class": record.class_id,
            "class_id": record.class_id,
            "user": record.user_id,
            "user_id": record.user_id,
            "title": record.title,
            "model": record.model,
            "start": record.started_at.isoformat() if record.started_at else None,
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

    if resource == "class":
        return {
            "id": record.id,
            "role": record.role,
            "name": record.name,
            "description": record.description,
            "instructor_id": record.instructor_id,
            "term": record.term,
            "section_code": record.section_code,
            "external_class_key": record.external_class_key,
            "section": {
                "term": record.term,
                "section_code": record.section_code,
            },
            "instructor": {
                "id": record.instructor_id,
            },
        }

    if resource == "feature":
        return {
            "id": record.id,
            "title": record.title,
            "description": record.description,
            "enabled": record.enabled,
            "instructor_id": record.instructor_id,
            "class_id": record.class_id,
        }

    if resource == "note":
        noted_on = record.noted_on.isoformat() if getattr(record, "noted_on", None) else None
        return {
            "id": record.id,
            "class": record.class_id,
            "class_id": record.class_id,
            "chat": record.chat_id,
            "chat_id": record.chat_id,
            "date": noted_on,
            "noted_on": noted_on,
            "content": record.content,
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


def _forbidden_response(message: str = "access denied"):
    return (
        jsonify(
            {
                "error": {
                    "code": "forbidden",
                    "message": message,
                    "details": {},
                }
            }
        ),
        403,
    )


def _raise_bad_request_from_exception(
    exc: Exception,
    *,
    source: str | None = None,
    message: str | None = None,
) -> None:
    details = {"exception": exc.__class__.__name__}
    if source:
        details["source"] = source
    raise BadRequestError(message or str(exc), details=details) from exc


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            _raise_bad_request_from_exception(
                exc,
                message="started_at must be an ISO-8601 datetime",
            )
    raise BadRequestError("started_at must be an ISO-8601 datetime")


def _parse_required_date(value: Any, *, field_name: str = "noted_on") -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            _raise_bad_request_from_exception(
                exc,
                message=f"{field_name} must be YYYY-MM-DD",
            )
    raise BadRequestError(f"{field_name} must be YYYY-MM-DD")


def _resolve_default_class_id_for_user(user_id: int) -> int | None:
    class_record = (
        db.session.query(CourseClass)
        .outerjoin(UserClassEnrollment, UserClassEnrollment.class_id == CourseClass.id)
        .filter(
            or_(
                CourseClass.instructor_id == user_id,
                and_(
                    UserClassEnrollment.user_id == user_id,
                    UserClassEnrollment.dropped_at.is_(None),
                ),
            )
        )
        .order_by(CourseClass.id.asc())
        .first()
    )
    return None if class_record is None else int(class_record.id)


def _parse_int_field(value: Any, *, field_name: str, required: bool = False) -> int | None:
    if value is None:
        if required:
            raise BadRequestError(f"{field_name} is required")
        return None

    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            if required:
                raise BadRequestError(f"{field_name} is required")
            return None
        value = trimmed

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        _raise_bad_request_from_exception(
            exc,
            message=f"{field_name} must be an integer",
        )


def _require_record(resource_name: str, model: Any, record_id: int) -> Any:
    record = db.session.get(model, record_id)
    if record is None:
        raise NotFoundError(f"{resource_name} not found", details={"id": record_id})
    return record


def _apply_chat_mutations(chat: Chat, payload: dict[str, Any]) -> None:
    if "class_id" in payload:
        class_record = _require_record("class", CourseClass, int(payload["class_id"]))
        chat.class_id = int(class_record.id)

    if "user_id" in payload:
        _require_record("user", User, int(payload["user_id"]))
        chat.user_id = int(payload["user_id"])

    if "title" in payload:
        chat.title = str(payload["title"] or "").strip() or chat.title

    if "model" in payload:
        chat.model = str(payload["model"] or "").strip() or chat.model

    if "started_at" in payload:
        parsed = _parse_optional_datetime(payload["started_at"])
        if parsed is not None:
            chat.started_at = parsed


def _apply_message_mutations(message: Message, payload: dict[str, Any]) -> None:
    if "chat_id" in payload:
        _require_record("chat", Chat, int(payload["chat_id"]))
        message.chat_id = int(payload["chat_id"])
    if "message_text" in payload:
        message.message_text = str(payload["message_text"] or "").strip()
    if "vote" in payload:
        message.vote = str(payload["vote"] or "").strip() or message.vote
    if "note" in payload:
        message.note = str(payload["note"] or "").strip() or message.note
    if "help_intent" in payload:
        message.help_intent = str(payload["help_intent"] or "").strip()


def _apply_class_mutations(class_record: CourseClass, payload: dict[str, Any]) -> None:
    for field in ("role", "name", "description", "term", "section_code", "external_class_key"):
        if field in payload:
            setattr(class_record, field, payload[field])

    if "instructor_id" in payload:
        _require_record("user", User, int(payload["instructor_id"]))
        class_record.instructor_id = int(payload["instructor_id"])


def _apply_feature_mutations(feature: Feature, payload: dict[str, Any]) -> None:
    for field in ("title", "description", "enabled", "instructor_id", "class_id"):
        if field in payload:
            setattr(feature, field, payload[field])


def _apply_note_mutations(note: Note, payload: dict[str, Any]) -> None:
    if "class_id" in payload:
        _require_record("class", CourseClass, int(payload["class_id"]))
        note.class_id = int(payload["class_id"])
    if "chat_id" in payload:
        _require_record("chat", Chat, int(payload["chat_id"]))
        note.chat_id = int(payload["chat_id"])
    if "noted_on" in payload:
        note.noted_on = _parse_required_date(payload["noted_on"])
    if "content" in payload:
        note.content = str(payload["content"] or "").strip()


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

    user = User(email=email, role=role, **build_transitional_identity_defaults(email))
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

    return jsonify({"message": "login successful", "user": {"id": user.id, "email": user.email, "role": user.role}}), 200


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
    return jsonify([_serialize_record("chat", chat) for chat in chats]), 200


@api_v1_bp.post("/chats")
@login_required
def create_chat():
    """Create a chat for the authenticated user in a class context."""
    payload = _deserialize_payload("chat", _read_json_object())
    authenticated_user_id = ChatAccessService.get_authenticated_user_id()

    class_id = _parse_int_field(payload.get("class_id"), field_name="class_id", required=False)
    if class_id is None:
        class_id = _resolve_default_class_id_for_user(authenticated_user_id)
        if class_id is None:
            raise BadRequestError("class_id is required")

    class_record = _require_record("class", CourseClass, class_id)

    requested_user_id = _parse_int_field(payload.get("user_id"), field_name="user_id", required=False)
    try:
        owner_user_id = ChatAccessService.assert_can_create_chat(
            class_record=class_record,
            actor_user_id=authenticated_user_id,
            requested_user_id=requested_user_id,
        )
    except PermissionError:
        return _forbidden_response("access denied")

    chat = Chat(
        class_id=int(class_id),
        user_id=owner_user_id,
        title=(payload.get("title") or "New Chat").strip(),
        model=(payload.get("model") or current_app.config.get("AI_MODEL_NAME") or "unknown").strip(),
    )
    started_at = _parse_optional_datetime(payload.get("started_at"))
    if started_at is not None:
        chat.started_at = started_at

    db.session.add(chat)
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 201


@api_v1_bp.get("/chats/<int:chat_id>")
@login_required
def get_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("user is not authorized for this chat")
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.put("/chats/<int:chat_id>")
@api_v1_bp.patch("/chats/<int:chat_id>")
@login_required
def update_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    try:
        ChatAccessService.assert_chat_owner(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("user is not authorized for this chat")

    payload = _deserialize_payload("chat", _read_json_object())
    _apply_chat_mutations(chat, payload)
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.delete("/chats/<int:chat_id>")
@login_required
def delete_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    try:
        ChatAccessService.assert_chat_owner(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("user is not authorized for this chat")

    response_payload = _serialize_record("chat", chat)
    db.session.delete(chat)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get("/messages")
@login_required
def list_messages():
    user_id = ChatAccessService.get_authenticated_user_id()
    messages = (
        db.session.query(Message)
        .join(Chat, Chat.id == Message.chat_id)
        .filter(Chat.user_id == user_id)
        .order_by(Message.id.asc())
        .all()
    )
    return jsonify([_serialize_record("message", m) for m in messages]), 200


@api_v1_bp.post("/messages")
@login_required
def create_message():
    payload = _deserialize_payload("message", _read_json_object())
    chat_id = payload.get("chat_id")
    if chat_id is None:
        raise BadRequestError("chat_id is required")

    chat = _require_record("chat", Chat, int(chat_id))
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    message = Message(
        chat_id=chat.id,
        message_text=str(payload.get("message_text") or "").strip(),
        vote=str(payload.get("vote") or "good").strip() or "good",
        note=str(payload.get("note") or "no").strip() or "no",
        help_intent=str(payload.get("help_intent") or "").strip(),
    )
    if not message.message_text:
        raise BadRequestError("message_text is required")
    if not message.help_intent:
        raise BadRequestError("help_intent is required")

    db.session.add(message)
    db.session.commit()
    return jsonify(_serialize_record("message", message)), 201


@api_v1_bp.get("/messages/<int:message_id>")
@login_required
def get_message(message_id: int):
    message = _require_record("message", Message, message_id)
    chat = _require_record("chat", Chat, message.chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    return jsonify(_serialize_record("message", message)), 200


@api_v1_bp.put("/messages/<int:message_id>")
@api_v1_bp.patch("/messages/<int:message_id>")
@login_required
def update_message(message_id: int):
    message = _require_record("message", Message, message_id)
    chat = _require_record("chat", Chat, message.chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    payload = _deserialize_payload("message", _read_json_object())
    _apply_message_mutations(message, payload)
    if not message.message_text:
        raise BadRequestError("message_text is required")
    if not message.help_intent:
        raise BadRequestError("help_intent is required")

    db.session.commit()
    return jsonify(_serialize_record("message", message)), 200


@api_v1_bp.delete("/messages/<int:message_id>")
@login_required
def delete_message(message_id: int):
    message = _require_record("message", Message, message_id)
    chat = _require_record("chat", Chat, message.chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    response_payload = _serialize_record("message", message)
    db.session.delete(message)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get("/chats/<int:chat_id>/messages")
@login_required
def list_chat_messages(chat_id: int):
    """List messages for a target chat when visible to the authenticated user."""
    chat = _require_record("chat", Chat, chat_id)
    try:
        ChatAccessService.assert_can_access_chat(
            chat=chat,
            user_id=ChatAccessService.get_authenticated_user_id(),
        )
    except PermissionError:
        return _forbidden_response("access denied")

    messages = (
        db.session.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.id.asc())
        .all()
    )
    return jsonify([_serialize_record("message", message) for message in messages]), 200


@api_v1_bp.post("/chats/<int:chat_id>/messages")
@login_required
def create_chat_message(chat_id: int):
    """Create a message on a target chat when writable by the current user."""
    chat = _require_record("chat", Chat, chat_id)
    try:
        ChatAccessService.assert_can_access_chat(
            chat=chat,
            user_id=ChatAccessService.get_authenticated_user_id(),
        )
    except PermissionError:
        return _forbidden_response("access denied")

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


@api_v1_bp.get("/classes")
@login_required
def list_classes():
    classes = db.session.query(CourseClass).order_by(CourseClass.id.asc()).all()
    return jsonify([_serialize_record("class", c) for c in classes]), 200


@api_v1_bp.post("/classes")
@login_required
def create_class():
    payload = _read_json_object()
    if payload.get("instructor_id") is None:
        payload["instructor_id"] = ChatAccessService.get_authenticated_user_id()

    class_record = CourseClass(
        role=str(payload.get("role") or "student"),
        name=str(payload.get("name") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        instructor_id=int(payload["instructor_id"]),
        term=payload.get("term"),
        section_code=payload.get("section_code"),
        external_class_key=payload.get("external_class_key"),
    )
    if not class_record.name or not class_record.description:
        raise BadRequestError("name and description are required")

    _require_record("user", User, class_record.instructor_id)
    db.session.add(class_record)
    db.session.commit()
    return jsonify(_serialize_record("class", class_record)), 201


@api_v1_bp.get("/classes/<int:class_id>")
@login_required
def get_class(class_id: int):
    class_record = _require_record("class", CourseClass, class_id)
    return jsonify(_serialize_record("class", class_record)), 200


@api_v1_bp.put("/classes/<int:class_id>")
@api_v1_bp.patch("/classes/<int:class_id>")
@login_required
def update_class(class_id: int):
    class_record = _require_record("class", CourseClass, class_id)
    payload = _read_json_object()
    _apply_class_mutations(class_record, payload)
    db.session.commit()
    return jsonify(_serialize_record("class", class_record)), 200


@api_v1_bp.delete("/classes/<int:class_id>")
@login_required
def delete_class(class_id: int):
    class_record = _require_record("class", CourseClass, class_id)
    response_payload = _serialize_record("class", class_record)
    db.session.delete(class_record)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get("/features")
@login_required
def list_features():
    features = db.session.query(Feature).order_by(Feature.id.asc()).all()
    return jsonify([_serialize_record("feature", feature) for feature in features]), 200


@api_v1_bp.post("/features")
@login_required
def create_feature():
    payload = _read_json_object()
    feature = Feature(
        title=str(payload.get("title") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        enabled=bool(payload.get("enabled", False)),
        instructor_id=payload.get("instructor_id"),
        class_id=payload.get("class_id"),
    )
    if not feature.title or not feature.description:
        raise BadRequestError("title and description are required")
    db.session.add(feature)
    db.session.commit()
    return jsonify(_serialize_record("feature", feature)), 201


@api_v1_bp.get("/features/<int:feature_id>")
@login_required
def get_feature(feature_id: int):
    feature = _require_record("feature", Feature, feature_id)
    return jsonify(_serialize_record("feature", feature)), 200


@api_v1_bp.put("/features/<int:feature_id>")
@api_v1_bp.patch("/features/<int:feature_id>")
@login_required
def update_feature(feature_id: int):
    feature = _require_record("feature", Feature, feature_id)
    payload = _read_json_object()
    _apply_feature_mutations(feature, payload)
    db.session.commit()
    return jsonify(_serialize_record("feature", feature)), 200


@api_v1_bp.delete("/features/<int:feature_id>")
@login_required
def delete_feature(feature_id: int):
    feature = _require_record("feature", Feature, feature_id)
    response_payload = _serialize_record("feature", feature)
    db.session.delete(feature)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get("/notes")
@login_required
def list_notes():
    user_id = ChatAccessService.get_authenticated_user_id()
    notes = (
        db.session.query(Note)
        .join(Chat, Chat.id == Note.chat_id)
        .filter(Chat.user_id == user_id)
        .order_by(Note.id.asc())
        .all()
    )
    return jsonify([_serialize_record("note", note) for note in notes]), 200


@api_v1_bp.post("/notes")
@login_required
def create_note():
    payload = _deserialize_payload("note", _read_json_object())
    class_id = payload.get("class_id")
    chat_id = payload.get("chat_id")
    if class_id is None or chat_id is None:
        raise BadRequestError("class_id and chat_id are required")

    _require_record("class", CourseClass, int(class_id))
    chat = _require_record("chat", Chat, int(chat_id))
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    note = Note(
        class_id=int(class_id),
        chat_id=int(chat_id),
        noted_on=_parse_required_date(payload.get("noted_on"), field_name="noted_on"),
        content=str(payload.get("content") or "").strip(),
    )
    if not note.content:
        raise BadRequestError("content is required")

    db.session.add(note)
    db.session.commit()
    return jsonify(_serialize_record("note", note)), 201


@api_v1_bp.get("/notes/<int:note_id>")
@login_required
def get_note(note_id: int):
    note = _require_record("note", Note, note_id)
    chat = _require_record("chat", Chat, note.chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")
    return jsonify(_serialize_record("note", note)), 200


@api_v1_bp.put("/notes/<int:note_id>")
@api_v1_bp.patch("/notes/<int:note_id>")
@login_required
def update_note(note_id: int):
    note = _require_record("note", Note, note_id)
    chat = _require_record("chat", Chat, note.chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    payload = _deserialize_payload("note", _read_json_object())
    _apply_note_mutations(note, payload)
    if not note.content:
        raise BadRequestError("content is required")

    db.session.commit()
    return jsonify(_serialize_record("note", note)), 200


@api_v1_bp.delete("/notes/<int:note_id>")
@login_required
def delete_note(note_id: int):
    note = _require_record("note", Note, note_id)
    chat = _require_record("chat", Chat, note.chat_id)
    try:
        ChatAccessService.assert_can_access_chat(chat=chat, user_id=ChatAccessService.get_authenticated_user_id())
    except PermissionError:
        return _forbidden_response("access denied")

    response_payload = _serialize_record("note", note)
    db.session.delete(note)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get("/health")
# Intentionally unauthenticated for liveness/readiness checks; rate limiting will follow.
def health():
    """Service heartbeat endpoint for deployment/readiness checks."""
    _publish("api.health_checked")
    return jsonify(
        {"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")}
    )


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
        _raise_bad_request_from_exception(
            exc,
            message="chat_id must be an integer",
        )


def _persist_ai_interaction(
    payload: dict[str, Any], prompt: str, result: Any
) -> tuple[Any, int] | None:
    """Persist an AI interaction; return error response tuple when persistence fails."""
    interaction_repo = AIInteractionRepository(AIInteraction)

    try:
        normalized = _normalize_interaction_response(result)
        interaction_repo.create(
            db.session,
            prompt=prompt,
            response_text=normalized["assistant_text"],
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
            "has_rag": bool(payload.get("rag")),
        },
    )

    initiated_by = _resolve_initiated_by(payload)

    # `ai_service` is registered during app startup in `app/__init__.py` via
    # `build_ai_service(...)`, which constructs `AIPipelineService` from
    # `app.services.ai_pipeline` and stores it at `app.extensions["ai_service"]`.
    #
    # Logging bootstrap may wrap that pipeline service in
    # `InteractionLoggingService`, but `run_interaction(...)` still delegates to
    # the same underlying `AIPipelineService` implementation.
    ai_service = current_app.extensions["ai_service"]

    try:
        result = ai_service.run_interaction(
            prompt=prompt,
            context=context_payload,
            initiated_by=initiated_by,
        )
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


register_api_view_route(api_v1_bp)
