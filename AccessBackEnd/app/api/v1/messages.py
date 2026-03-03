from typing import Any

from flask import jsonify
from flask_login import login_required

from .routes import (
    _assert_chat_permissions,
    _apply_field_updates,
    _deserialize_payload,
    _forbidden_response,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    BadRequestError,
    api_v1_bp,
    db,
)
from .schemas.validation import MessagePayloadSchema, PartialMessagePayloadSchema
from ...models import Chat, Message
from ...services.chat_access_service import ChatAccessService

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
        vote=payload['vote'],
        note=payload['note'],
        help_intent=payload['help_intent'],
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
    payload = _validate_payload(_deserialize_payload("message", _read_json_object()), MessagePayloadSchema())
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
        vote=payload['vote'],
        note=payload['note'],
        help_intent=payload['help_intent'],
    )

    db.session.add(message)
    db.session.commit()
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
    return jsonify([_serialize_record("message", message) for message in messages]), 200

#HELPERs
def _apply_message_mutations(message: Message, payload: dict[str, Any]) -> None:
    if "chat_id" in payload:
        _require_record("chat", Chat, int(payload["chat_id"]))
        message.chat_id = int(payload["chat_id"])
    _apply_field_updates(
        message,
        payload,
        (
            "message_text",
            'vote',
            'note',
            'help_intent'
        )
    )

