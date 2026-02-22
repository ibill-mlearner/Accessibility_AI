from flask import jsonify, current_app
from flask_login import login_required, current_user

from .routes import db, _serialize_record, BadRequestError, _require_record, _resolve_default_class_id_for_user, \
    _parse_int_field, _deserialize_payload, _read_json_object, api_v1_bp, _forbidden_response, _parse_optional_datetime, \
    Chat
from ...models import CourseClass, User
from ...services.chat_access_service import ChatAccessService

from typing import Any

@api_v1_bp.get("/chats")
@login_required
# Requires a valid Flask-Login session cookie on the incoming request.
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
