from typing import Any

from flask import jsonify
from flask_login import login_required

from .routes import (
    _apply_field_updates,
    BadRequestError,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    api_v1_bp,
    db,
)
from .schemas.validation import ClassPayloadSchema, PartialClassPayloadSchema
from ...models import CourseClass, User
from ...services.chat_access_service import ChatAccessService


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

    payload = _validate_payload(payload, ClassPayloadSchema())

    class_record = CourseClass(
        name=payload["name"],
        description=payload["description"],
        instructor_id=payload["instructor_id"],
        active=payload["active"],
    )


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
    payload = _validate_payload(_read_json_object(), PartialClassPayloadSchema())
    _apply_class_mutations(class_record, payload)
    if not class_record.name or not class_record.description:
        raise BadRequestError("name and description are required")
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

def _apply_class_mutations(class_record: CourseClass, payload: dict[str, Any]) -> None:
    _apply_field_updates(
        class_record,
        payload,
        (
            'name',
            'description',
            'active'
        )
    )

    if "instructor_id" in payload:
        _require_record("user", User, int(payload["instructor_id"]))
        class_record.instructor_id = int(payload["instructor_id"])
