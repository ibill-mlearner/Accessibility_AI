from __future__ import annotations

from flask import jsonify
from flask_login import login_required

from .routes import (
    _parse_int_field,
    _read_json_object,
    _require_record,
    _serialize_record,
    api_v1_bp,
    db,
)
from ...models import Accommodation, AccommodationSystemPrompt, SystemPrompt


@api_v1_bp.get("/accommodation-system-prompt-links")
@login_required
def list_accommodation_system_prompt_links():
    links = db.session.query(AccommodationSystemPrompt).order_by(AccommodationSystemPrompt.id.asc()).all()
    return jsonify([_serialize_record("accommodation_system_prompt_link", link) for link in links]), 200


@api_v1_bp.post("/accommodation-system-prompt-links")
@login_required
def create_accommodation_system_prompt_link():
    payload = _read_json_object()

    #todo: Restrict writes to instructor/admin roles and class ownership.
    accommodation_id = _parse_int_field(payload.get("accommodation_id"), field_name="accommodation_id", required=True)
    system_prompt_id = _parse_int_field(payload.get("system_prompt_id"), field_name="system_prompt_id", required=True)

    _require_record("accommodation", Accommodation, accommodation_id)
    _require_record("system_prompt", SystemPrompt, system_prompt_id)

    link = AccommodationSystemPrompt(accommodation_id=accommodation_id, system_prompt_id=system_prompt_id)
    db.session.add(link)
    db.session.commit()
    return jsonify(_serialize_record("accommodation_system_prompt_link", link)), 201


@api_v1_bp.get("/accommodation-system-prompt-links/<int:link_id>")
@login_required
def get_accommodation_system_prompt_link(link_id: int):
    link = _require_record("accommodation_system_prompt_link", AccommodationSystemPrompt, link_id)
    return jsonify(_serialize_record("accommodation_system_prompt_link", link)), 200


@api_v1_bp.patch("/accommodation-system-prompt-links/<int:link_id>")
@login_required
def update_accommodation_system_prompt_link(link_id: int):
    link = _require_record("accommodation_system_prompt_link", AccommodationSystemPrompt, link_id)
    payload = _read_json_object()

    #todo: Restrict writes to instructor/admin roles and class ownership.
    if "accommodation_id" in payload:
        accommodation_id = _parse_int_field(payload.get("accommodation_id"), field_name="accommodation_id", required=True)
        _require_record("accommodation", Accommodation, accommodation_id)
        link.accommodation_id = accommodation_id

    if "system_prompt_id" in payload:
        system_prompt_id = _parse_int_field(payload.get("system_prompt_id"), field_name="system_prompt_id", required=True)
        _require_record("system_prompt", SystemPrompt, system_prompt_id)
        link.system_prompt_id = system_prompt_id

    db.session.commit()
    return jsonify(_serialize_record("accommodation_system_prompt_link", link)), 200


@api_v1_bp.delete("/accommodation-system-prompt-links/<int:link_id>")
@login_required
def delete_accommodation_system_prompt_link(link_id: int):
    link = _require_record("accommodation_system_prompt_link", AccommodationSystemPrompt, link_id)

    #todo: Restrict writes to instructor/admin roles and class ownership.
    response_payload = _serialize_record("accommodation_system_prompt_link", link)
    db.session.delete(link)
    db.session.commit()
    return jsonify(response_payload), 200