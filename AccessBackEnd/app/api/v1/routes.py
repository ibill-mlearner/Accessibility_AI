from __future__ import annotations
from datetime import date, datetime
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import and_, or_
from marshmallow import Schema, ValidationError
from ..errors import BadRequestError, NotFoundError
from .api_view import register_api_view_route
from ...extensions import db
from ...models import CourseClass, UserClassEnrollment
from ...services.logging import DomainEvent

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

_RESOURCE_API_TO_MODEL_FIELDS: dict[str, dict[str, str]] = {
    "chat": {
        "class": "class_id",
        "class_id": "class_id",
        "user": "user_id",
        "user_id": "user_id",
        "start": "started_at",
        "started_at": "started_at",
        "title": "title",
        "model": "model",
    },
    "message": {
        "chat": "chat_id",
        "chat_id": "chat_id",
        "text": "message_text",
        "message_text": "message_text",
        "vote": "vote",
        "note": "note",
        "help_intent": "help_intent",
    },
    "note": {
        "class": "class_id",
        "class_id": "class_id",
        "chat": "chat_id",
        "chat_id": "chat_id",
        "date": "noted_on",
        "noted_on": "noted_on",
        "content": "content",
    },
}


def _deserialize_payload(
    resource: str, 
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Map API payload keys onto model field names for CRUD operations."""
    field_map = _RESOURCE_API_TO_MODEL_FIELDS.get(resource, {})
    return {field_map.get(key, key): value for key, value in payload.items()}

def _validate_payload(
    payload: dict[str, Any], 
    schema: Schema
) -> dict[str, Any]:
    """Validate and normalize request payloads using Marshmallow schemas."""

    try:
        return schema.load(payload)
    except ValidationError as exc:
        raise BadRequestError("request validation failed", details={"fields": exc.messages}) from exc

def _serialize_record(
    resource: str, 
    record: Any
) -> dict[str, Any]:
    """Serialize ORM objects using API field names for stable endpoint envelopes."""
    if resource == "chat":
        return {
            "id": record.id,
            "class": record.class_id,
            "class_id": record.class_id,
            "user": record.user_id,
            "user_id": record.user_id,
            "title": record.title,
            "model": record.model,
            "start": record.started_at.isoformat() if record.started_at else None,
            "started_at": record.started_at.isoformat() if record.started_at else None,
        }

    if resource == "message":
        return {
            "id": record.id,
            "chat_id": record.chat_id,
            "message_text": record.message_text,
            "vote": record.vote,
            "note": record.note,
            "help_intent": record.help_intent,
        }

    if resource == "class":
        return {
            "id": record.id,
                        "name": record.name,
            "description": record.description,
            "instructor_id": record.instructor_id,
            "active": record.active,
        }

    if resource == "feature":
        details = record.details
        active = record.active
        return {
            "id": record.id,
            "title": record.title,
            "details": details,
            "active": active,
            "description": details,
            "enabled": active
        }

    if resource == "note":
        noted_on = record.noted_on.isoformat() if getattr(record, "noted_on", None) else None
        return {
            "id": record.id,
            "class": record.class_id,
            "class_id": record.class_id,
            "chat": record.chat_id,
            "chat_id": record.chat_id,
            "date": noted_on,
            "noted_on": noted_on,
            "content": record.content,
        }

    if resource == "ai_interaction":
        created_at = record.created_at.isoformat() if getattr(record, "created_at", None) else None
        return {
            "id": record.id,
            "chat_id": record.chat_id,
            "prompt": record.prompt,
            "response_text": record.response_text,
            "ai_model_id": record.ai_model_id,
            "provider": record.ai_model.provider if getattr(record, "ai_model", None) else None,
            "accommodations_id_system_prompts_id": record.accommodations_id_system_prompts_id,
            "created_at": created_at,
        }

    if resource == "system_prompt":
        return {
            "id": record.id,
            "text": record.text,
            "class_id": record.class_id,
            "instructor_id": record.instructor_id,
        }
    if resource == "accommodation_system_prompt_link":
        return {
            "id": record.id,
            "accommodation_id": record.accommodation_id,
            "system_prompt_id": record.system_prompt_id,
            # Optional denormalized fields for selection UIs.
            "accommodation_title": record.accommodation.title if getattr(record, "accommodation", None) else None,
            "system_prompt_text": record.system_prompt.text if getattr(record, "system_prompt", None) else None,
        }


    return {}


def _publish(
    event_name: str, 
    payload: dict[str, Any] | None = None
) -> None:
    """Publish a domain event for endpoint observability."""
    current_app.extensions["event_bus"].publish(DomainEvent(event_name, payload or {}))


def _read_json_object() -> dict[str, Any]:
    """Read request JSON body and require object payloads for route stubs."""
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequestError("json body required")
    if not isinstance(payload, dict):
        raise BadRequestError("json object body required")
    return payload


def _forbidden_response(
    message: str = "access denied"
):
    return (
        jsonify(
            {
                "error": {
                    "code": "forbidden",
                    "message": message,
                    "details": {},
                }
            }
        ),
        403,
    )


def _raise_bad_request_from_exception(
    exc: Exception,
    *,
    source: str | None = None,
    message: str | None = None,
) -> None:
    details = {"exception": exc.__class__.__name__}
    if source:
        details["source"] = source
    raise BadRequestError(message or str(exc), details=details) from exc


def _parse_optional_datetime(
    value: Any
) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            _raise_bad_request_from_exception(
                exc,
                message="started_at must be an ISO-8601 datetime",
            )
    raise BadRequestError("started_at must be an ISO-8601 datetime")


def _parse_required_date(
    value: Any, *, 
    field_name: str = "noted_on"
) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            _raise_bad_request_from_exception(
                exc,
                message=f"{field_name} must be YYYY-MM-DD",
            )
    raise BadRequestError(f"{field_name} must be YYYY-MM-DD")


def _resolve_default_class_id_for_user(
    user_id: int
) -> int | None:
    class_record = (
        db.session.query(CourseClass)
        .outerjoin(UserClassEnrollment, UserClassEnrollment.class_id == CourseClass.id)
        .filter(
            or_(
                CourseClass.instructor_id == user_id,
                and_(
                    UserClassEnrollment.user_id == user_id,
                    UserClassEnrollment.active.is_(True),
                ),
            )
        )
        .order_by(CourseClass.id.asc())
        .first()
    )
    return None if class_record is None else int(class_record.id)


def _parse_int_field(
    value: Any, *,
    field_name: str, 
    required: bool = False
) -> int | None:
    if value is None:
        if required:
            raise BadRequestError(f"{field_name} is required")
        return None

    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            if required:
                raise BadRequestError(f"{field_name} is required")
            return None
        value = trimmed

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        _raise_bad_request_from_exception(
            exc,
            message=f"{field_name} must be an integer",
        )


def _require_record(
    resource_name: str, 
    model: Any, 
    record_id: int
) -> Any:
    record = db.session.get(model, record_id)
    if record is None:
        raise NotFoundError(f"{resource_name} not found", details={"id": record_id})
    return record

def _apply_field_updates(
    record: Any, 
    payload: dict[str, Any], 
    fields: tuple[str, ...]
) -> None:
    """Apply partial payload field updates onto a mutable ORM record."""
    for field in fields:
        if field in payload:
            setattr(record, field, payload[field])



@api_v1_bp.get("/health")
# Intentionally unauthenticated for liveness/readiness checks; rate limiting will follow.
def health():
    """Service heartbeat endpoint for deployment/readiness checks."""
    _publish("api.health_checked")
    return jsonify(
        {"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")}
    )

register_api_view_route(api_v1_bp)

