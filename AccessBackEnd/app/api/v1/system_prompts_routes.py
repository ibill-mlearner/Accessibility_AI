from flask import jsonify
from flask_login import login_required

from .routes import (
    _apply_field_updates,
    _parse_int_field,
    _read_json_object,
    _require_record,
    _serialize_record,
    api_v1_bp,
    db,
    BadRequestError,
)
from ...models import CourseClass, SystemPrompt, User
from ...utils.api_checker import _enforce_roles
from ...utils.api_checker import ensure_instructor_owns_system_prompt_class


@api_v1_bp.get("/system-prompts")
@login_required
def list_system_prompts():
    prompts = db.session.query(SystemPrompt).order_by(SystemPrompt.id.asc()).all()
    return jsonify([_serialize_record("system_prompt", prompt) for prompt in prompts]), 200


@api_v1_bp.post("/system-prompts")
@login_required
def create_system_prompt():
    denied = _enforce_roles("admin", "instructor")
    if denied is not None:
        return denied
    payload = _read_json_object()

    #todo: Restrict writes to instructor/admin roles and class ownership.
    class_id = _parse_int_field(payload.get("class_id"), field_name="class_id")
    instructor_id = _parse_int_field(payload.get("instructor_id"), field_name="instructor_id")
    text = str(payload.get("text") or "").strip()
    if not text:
        raise BadRequestError("text is required")

    if class_id is not None:
        _require_record("class", CourseClass, class_id)

    denied = ensure_instructor_owns_system_prompt_class(class_id=class_id, action="create")
    if denied is not None:
        return denied


    if instructor_id is not None:
        _require_record("user", User, instructor_id)

    prompt = SystemPrompt(class_id=class_id, instructor_id=instructor_id, text=text)
    db.session.add(prompt)
    db.session.commit()
    return jsonify(_serialize_record("system_prompt", prompt)), 201


@api_v1_bp.get("/system-prompts/<int:prompt_id>")
@login_required
def get_system_prompt(prompt_id: int):
    prompt = _require_record("system_prompt", SystemPrompt, prompt_id)
    return jsonify(_serialize_record("system_prompt", prompt)), 200


@api_v1_bp.patch("/system-prompts/<int:prompt_id>")
@login_required
def update_system_prompt(prompt_id: int):
    denied = _enforce_roles("admin", "instructor")
    if denied is not None:
        return denied
    prompt = _require_record("system_prompt", SystemPrompt, prompt_id)
    payload = _read_json_object()

    #todo: Restrict writes to instructor/admin roles and class ownership.
    resolved_class_id = prompt.class_id
    if "class_id" in payload:
        class_id = _parse_int_field(payload.get("class_id"), field_name="class_id")
        if class_id is not None:
            _require_record("class", CourseClass, class_id)
        payload["class_id"] = class_id
        resolved_class_id = class_id

    denied = ensure_instructor_owns_system_prompt_class(class_id=resolved_class_id, action="update")
    if denied is not None:
        return denied

    if "instructor_id" in payload:
        instructor_id = _parse_int_field(payload.get("instructor_id"), field_name="instructor_id")
        if instructor_id is not None:
            _require_record("user", User, instructor_id)
        payload['instructor_id'] = instructor_id

    _apply_field_updates(
        prompt,
        payload,
        (
            'class_id',
            'instructor_id'
        )
    )

    if "text" in payload:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise BadRequestError("text is required")
        prompt.text = text

    db.session.commit()
    return jsonify(_serialize_record("system_prompt", prompt)), 200


@api_v1_bp.delete("/system-prompts/<int:prompt_id>")
@login_required
def delete_system_prompt(prompt_id: int):
    
    denied = _enforce_roles("admin", "instructor")
    if denied is not None:
        return denied
    prompt = _require_record("system_prompt", SystemPrompt, prompt_id)

    denied = ensure_instructor_owns_system_prompt_class(class_id=prompt.class_id, action="delete")
    if denied is not None:
        return denied
    response_payload = _serialize_record("system_prompt", prompt)
    db.session.delete(prompt)
    db.session.commit()
    return jsonify(response_payload), 200
