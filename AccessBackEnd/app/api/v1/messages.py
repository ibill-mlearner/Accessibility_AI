from flask_login import login_required
from flask import jsonify
from .routes import (
_require_record,
ChatAccessService,
Chat,
_forbidden_response,
_deserialize_payload,
_read_json_object,
api_v1_bp,
BadRequestError,
Message,
db,
_serialize_record
)

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

