from __future__ import annotations

from flask import jsonify
from flask_login import current_user

from ..api.v1.routes import db
from ..models import CourseClass, SystemPrompt


def forbidden_scope_response(
    message: str,
    *,
    action: str,
    class_id: int | None,
    system_prompt_id: int | None = None,
):
    details = {
        "action": action,
        "class_id": class_id,
        "current_role": (getattr(current_user, "role", "") or "").strip().lower() or None,
        "current_user_id": int(current_user.id),
    }
    if system_prompt_id is not None:
        details["system_prompt_id"] = system_prompt_id

    return (
        jsonify(
            {
                "error": "forbidden",
                "message": message,
                "details": details,
            }
        ),
        403,
    )


def ensure_instructor_owns_system_prompt_class(*, class_id: int | None, action: str):
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if role != "instructor":
        return None

    if class_id is None:
        return forbidden_scope_response(
            "instructors can only manage system prompts tied to classes they own",
            action=action,
            class_id=None,
        )

    class_record = db.session.get(CourseClass, int(class_id))
    if class_record is None or int(class_record.instructor_id) != int(current_user.id):
        return forbidden_scope_response(
            "instructors can only manage system prompts for classes they own",
            action=action,
            class_id=class_id,
        )

    return None


def ensure_instructor_owns_system_prompt_scope(*, system_prompt: SystemPrompt, action: str):
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if role != "instructor":
        return None

    class_id = system_prompt.class_id
    if class_id is None:
        return forbidden_scope_response(
            "instructors can only manage links for class-scoped system prompts they own",
            action=action,
            class_id=None,
            system_prompt_id=int(system_prompt.id),
        )

    class_record = db.session.get(CourseClass, int(class_id))
    if class_record is None or int(class_record.instructor_id) != int(current_user.id):
        return forbidden_scope_response(
            "instructors can only manage links for classes they own",
            action=action,
            class_id=class_id,
            system_prompt_id=int(system_prompt.id),
        )

    return None