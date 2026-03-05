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
from ...services.chat_access_service import ChatAccessService
from ...helpers.mutations import _apply_chat_mutations

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
    payload = _validate_payload( 
        _deserialize_payload("chat", _read_json_object()), ChatPayloadSchema())
    authenticated_user_id = ChatAccessService.get_authenticated_user_id()

    class_id = payload.get("class_id")
    if class_id is None:
        class_id = _resolve_default_class_id_for_user(authenticated_user_id)
        if class_id is None:
            raise BadRequestError("class_id is required")

    class_record = _require_record("class", CourseClass, class_id)

    requested_user_id = payload.get("user_id")
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
        title=payload.get("title") or "New Chat",
        model=payload.get("model") or current_app.config.get("AI_MODEL_NAME") or "unknown",
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
    deny = _assert_chat_permissions(chat, message="user is not authorized for this chat")
    if deny is not None:
        return deny
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.put("/chats/<int:chat_id>")
@api_v1_bp.patch("/chats/<int:chat_id>")
@login_required
def update_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat, message="user is not authorized for this chat")
    if deny is not None:
        return deny

    payload = _validate_payload( 
        _deserialize_payload(
            "chat", _read_json_object()), ChatPayloadSchema(partial=True))
    
    _apply_chat_mutations(chat, payload)
    db.session.commit()
    return jsonify(_serialize_record("chat", chat)), 200


@api_v1_bp.delete("/chats/<int:chat_id>")
@login_required
def delete_chat(chat_id: int):
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat, message="user is not authorized for this chat")
    if deny is not None:
        return deny

    response_payload = _serialize_record("chat", chat)
    db.session.delete(chat)
    db.session.commit()
    return jsonify(response_payload), 200
