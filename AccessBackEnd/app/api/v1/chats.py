from flask import current_app, jsonify
from flask_login import current_user, login_required

from .routes import (
    _assert_chat_permissions,
    _deserialize_payload,
    _forbidden_response,
    _parse_optional_datetime,
    _read_json_object,
    _require_record,
    _resolve_default_class_id_for_user,
    _serialize_record,
    _validate_payload,
    BadRequestError,
    api_v1_bp,
    db,
)
from ...schemas.validation import ChatPayloadSchema
from ...models import Chat, CourseClass
from ...utils.chat_access import ChatAccessHelper
from ...utils.api_checker import _apply_chat_mutations


MAX_CHAT_TITLE_WORDS = 20


def _normalize_chat_title(title: str) -> str:
    return " ".join(str(title or "").strip().split())


def _validate_chat_title_word_limit(title: str) -> str:
    normalized_title = _normalize_chat_title(title)
    if len(normalized_title.split()) > MAX_CHAT_TITLE_WORDS:
        raise BadRequestError(f"title must be at most {MAX_CHAT_TITLE_WORDS} words")
    return normalized_title


@api_v1_bp.get("/chats")
@login_required
# Requires a valid Flask-Login session cookie on the incoming request.
def list_chats():
    """List chats for the authenticated user in a stable collection envelope."""

    user_id = int(current_user.get_id())
    chats = (
        db.session.query(Chat)
        .filter(Chat.user_id == user_id)
        .filter(Chat.active.is_(True))
        .order_by(Chat.started_at.desc(), Chat.id.desc())
        .all()
    )
    return jsonify([_serialize_record("chat", chat) for chat in chats]), 200


@api_v1_bp.post("/chats")
@login_required
def create_chat():
    """Create a chat for the authenticated user in a class context."""
    payload = _validate_payload( 
        _deserialize_payload("chat", _read_json_object()), ChatPayloadSchema())
    authenticated_user_id = ChatAccessHelper.get_authenticated_user_id()

    class_id = payload.get("class_id")
    if class_id is None:
        class_id = _resolve_default_class_id_for_user(authenticated_user_id)
        if class_id is None:
            raise BadRequestError("class_id is required")

    class_record = _require_record("class", CourseClass, class_id)

    requested_user_id = payload.get("user_id")
    try:
        owner_user_id = ChatAccessHelper.assert_can_create_chat(
            class_record=class_record,
            actor_user_id=authenticated_user_id,
            requested_user_id=requested_user_id,
        )
    except PermissionError:
        return _forbidden_response("access denied")

    chat = Chat(
        class_id=int(class_id),
        user_id=owner_user_id,
        title=_validate_chat_title_word_limit(payload.get("title") or "New Chat"),
        model=payload.get("model") or current_app.config.get("AI_MODEL_NAME") or "unknown",
        active=True,
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
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.put("/chats/<int:chat_id>")
@api_v1_bp.patch("/chats/<int:chat_id>")
@login_required
def update_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    payload = _validate_payload( 
        _deserialize_payload(
            "chat", _read_json_object()), ChatPayloadSchema(partial=True))

    if "title" in payload and payload["title"] is not None:
        payload["title"] = _validate_chat_title_word_limit(payload["title"])

    _apply_chat_mutations(chat, payload)
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.patch("/chats/<int:chat_id>/archive")
@login_required
def archive_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    chat.active = False
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.patch("/chats/<int:chat_id>/edit-title")
@login_required
def edit_chat_title(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    payload = _read_json_object()
    if "title" not in payload:
        raise BadRequestError("title is required")

    chat.title = _validate_chat_title_word_limit(payload.get("title"))
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.delete("/chats/<int:chat_id>")
@login_required
def delete_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    response_payload = _serialize_record("chat", chat)
    db.session.delete(chat)
    db.session.commit()
    return jsonify(response_payload), 200
