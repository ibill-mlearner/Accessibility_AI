from flask import jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from .routes import (
    BadRequestError,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    api_v1_bp,
    db,
)
from ...schemas.validation import ClassPayloadSchema, PartialClassPayloadSchema
from ...models import CourseClass, User
from ...models.learning import UserClassEnrollment
from ...utils.chat_access import ChatAccessHelper
from ...utils.api_checker import _apply_class_mutations
from ...utils.api_checker import _enforce_roles


@api_v1_bp.get("/classes/instructors")
@login_required
def list_class_instructors():
    denied = _enforce_roles("admin")
    if denied is not None:
        return denied
    instructors = (
        db.session.query(User)
        .filter(User.role == "instructor")
        .order_by(User.email.asc())
        .all()
    )
    payload = [{"id": int(instructor.id), "email": instructor.email} for instructor in instructors]
    return jsonify(payload), 200


@api_v1_bp.get("/classes")
@login_required
def list_classes():
    user_id = ChatAccessHelper.get_authenticated_user_id()
    role = (getattr(current_user, "role", "") or "").strip().lower()

    base_query = db.session.query(CourseClass)
    if role == "admin":
        classes = base_query.order_by(CourseClass.id.asc()).all()
    elif role == "instructor":
        classes = (
            base_query
            .outerjoin(UserClassEnrollment, UserClassEnrollment.class_id == CourseClass.id)
            .filter(
                or_(
                    CourseClass.instructor_id == user_id,
                    and_(
                        UserClassEnrollment.user_id == user_id,
                        UserClassEnrollment.active.is_(True)
                    )
                )
            )
            .distinct()
            .order_by(CourseClass.id.asc())
            .all()

        )
    else:
        classes = (
            base_query
            .join(UserClassEnrollment, UserClassEnrollment.class_id == CourseClass.id)
            .filter(
                UserClassEnrollment.user_id == user_id,
                UserClassEnrollment.active.is_(True)
            )
            .distinct()
            .order_by(CourseClass.id.asc())
            .all()
        )

    # classes = db.session.query(CourseClass).order_by(CourseClass.id.asc()).all()
    return jsonify([_serialize_record("class", c) for c in classes]), 200


@api_v1_bp.post("/classes")
@login_required
def create_class():
    denied = _enforce_roles("admin")
    if denied is not None:
        return denied
    payload = _read_json_object()
    if payload.get("instructor_id") is None:
        payload["instructor_id"] = ChatAccessHelper.get_authenticated_user_id()

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

    denied = _enforce_roles("admin", "instructor")
    if denied is not None:
        return denied

    if getattr(current_user, "role", "").strip().lower() == "instructor":
        if int(class_record.instructor_id) != int(current_user.id):
            return jsonify({
                "error": "forbidden",
                "message": "instructors can only update classes they own"
            }), 403

    payload = _validate_payload(_read_json_object(), PartialClassPayloadSchema())

    if "instructor_id" in payload and getattr(current_user, "role", "").strip().lower() != "admin":
        return jsonify({
            "error": "forbidden",
            "message": "only amins can reassign class instructors"
        }), 403

    _apply_class_mutations(class_record, payload)
    if not class_record.name or not class_record.description:
        raise BadRequestError("name and description are required")

    db.session.commit()
    return jsonify(_serialize_record("class", class_record)), 200


@api_v1_bp.delete("/classes/<int:class_id>")
@login_required
def delete_class(class_id: int):
    deneid = _enforce_roles("admin")
    if deneid is not None:
        return deneid

    class_record = _require_record("class", CourseClass, class_id)
    response_payload = _serialize_record("class", class_record)
    db.session.delete(class_record)
    db.session.commit()
    return jsonify(response_payload), 200
