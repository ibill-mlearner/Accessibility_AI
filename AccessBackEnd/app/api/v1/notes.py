from flask import jsonify
from flask_login import login_required
from typing import Any
from .routes import (
    api_v1_bp,
    db,
    _assert_chat_permissions,
    _serialize_record,
    _deserialize_payload,
    _read_json_object,
    BadRequestError,
    _require_record,
    CourseClass,
    _forbidden_response,
    _parse_required_date
)
from ...services.chat_access_service import ChatAccessService
from ...models import Note, Chat


#ROUTES
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
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

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
    user_id = ChatAccessService.get_authenticated_user_id()
    note = _require_record("note", Note, note_id)
    chat = _require_record("chat", Chat, note.chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny
    return jsonify(_serialize_record("note", note)), 200


@api_v1_bp.put("/notes/<int:note_id>")
@api_v1_bp.patch("/notes/<int:note_id>")
@login_required
def update_note(note_id: int):
    note = _require_record("note", Note, note_id)
    chat = _require_record("chat", Chat, note.chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    payload = _deserialize_payload("note", _read_json_object())
    _apply_note_mutations(note, payload, user_id=user_id)
    if not note.content:
        raise BadRequestError("content is required")

    db.session.commit()
    return jsonify(_serialize_record("note", note)), 200


@api_v1_bp.delete("/notes/<int:note_id>")
@login_required
def delete_note(note_id: int):
    user_id = ChatAccessService.get_authenticated_user_id()
    note = _require_record("note", Note, note_id)
    chat = _require_record("chat", Chat, note.chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    response_payload = _serialize_record("note", note)
    db.session.delete(note)
    db.session.commit()
    return jsonify(response_payload), 200

#HELPERS
def _apply_note_mutations(note: Note, payload: dict[str, Any]) -> None:
    if "class_id" in payload:
        _require_record("class", CourseClass, int(payload["class_id"]))
        note.class_id = int(payload["class_id"])
    if "chat_id" in payload:
        chat = _require_record("chat", Chat, int(payload['chat_id']))
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            # return deny
            raise BadRequestError("chat id is not accessible")
        note.chat_id = int(payload["chat_id"])
    if "noted_on" in payload:
        note.noted_on = _parse_required_date(payload["noted_on"], field_name="noted_on")
    if "content" in payload:
        note.content = str(payload["content"] or "").strip()
