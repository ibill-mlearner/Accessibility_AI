from flask import jsonify, current_app, request
from flask_login import login_required, current_user

from .routes import (
    _assert_chat_permissions,
    _deserialize_payload,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    BadRequestError,
    api_v1_bp,
    db,
)
from ...schemas.validation import MessagePayloadSchema, PartialMessagePayloadSchema
from ...models import Chat, Message
from ...utils.chat_access import ChatAccessHelper
from ...utils.api_checker import _apply_message_mutations

@api_v1_bp.post("/chats/<int:chat_id>/messages")
@login_required
def create_chat_message(chat_id: int):
    """Create a message on a target chat when writable by the current user."""
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    payload = _validate_payload(_deserialize_payload("message", _read_json_object()), MessagePayloadSchema())



    message = Message(
        chat_id=chat_id,
        message_text=payload["message_text"],
        vote=payload.get('vote') or 'good',
        note=payload.get('note') or 'no',
        help_intent=payload.get('help_intent') or 'summarization'
    )
    db.session.add(message)
    db.session.commit()
    return jsonify(_serialize_record("message", message)), 201

@api_v1_bp.get("/messages")
@login_required
def list_messages():
    user_id = ChatAccessHelper.get_authenticated_user_id()
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
    payload_raw = _read_json_object()
    user_identity = getattr(current_user, "email", None) or getattr(current_user, "id", None) or "anonymous"
    current_app.logger.debug(
        "api.messages.create.request method=%s path=%s user=%s json_keys=%s",
        request.method,
        request.path,
        user_identity,
        sorted(payload_raw.keys()),
    )
    payload = _validate_payload(_deserialize_payload("message", payload_raw), MessagePayloadSchema())
    chat_id = payload.get("chat_id")
    if chat_id is None:
        raise BadRequestError("chat_id is required")

    chat = _require_record("chat", Chat, int(chat_id))
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    message = Message(
        chat_id=chat_id,
        message_text=payload["message_text"],
        vote=payload.get("vote") or "good",
        note=payload.get("note") or "no",
        help_intent=payload.get("help_intent") or "summarization"
    )
    try:
        print(message)
    except:
        pass
    db.session.add(message)
    db.session.commit()
    current_app.logger.debug(
        "api.messages.create.response path=%s status=%s message_id=%s message=%s",
        request.path,
        201,
        message.id,
        message.chat
    )
    return jsonify(_serialize_record("message", message)), 201


@api_v1_bp.get("/messages/<int:message_id>")
@login_required
def get_message(message_id: int):
    message = _require_record("message", Message, message_id)
    chat = _require_record("chat", Chat, message.chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    return jsonify(_serialize_record("message", message)), 200


@api_v1_bp.put("/messages/<int:message_id>")
@api_v1_bp.patch("/messages/<int:message_id>")
@login_required
def update_message(message_id: int):
    message = _require_record("message", Message, message_id)
    chat = _require_record("chat", Chat, message.chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    payload = _validate_payload(_deserialize_payload("message", _read_json_object()), MessagePayloadSchema())
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
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    response_payload = _serialize_record("message", message)
    db.session.delete(message)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get("/chats/<int:chat_id>/messages")
@login_required
def list_chat_messages(chat_id: int):
    """List messages for a target chat when visible to the authenticated user."""
    current_app.logger.debug(
        "api.chat_messages.list.request method=%s path=%s user_id=%s",
        request.method,
        request.path,
        ChatAccessHelper.get_authenticated_user_id(),
    )
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    messages = (
        db.session.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.id.asc())
        .all()
    )

    current_app.logger.debug(
        "api.chat_messages.list.response path=%s status=%s count=%s", 
        request.path, 
        200, 
        len(messages)
    )
    return jsonify([_serialize_record("message", message) for message in messages]), 200

