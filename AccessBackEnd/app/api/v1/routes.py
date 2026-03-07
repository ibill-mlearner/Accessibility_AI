from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from ..errors import BadRequestError, NotFoundError
from ...extensions import db
from ...models import CourseClass
from ...helpers.route_helpers import (
    _apply_field_updates,
    _assert_chat_permissions,
    _deserialize_payload,
    _forbidden_response,
    _parse_int_field,
    _parse_optional_datetime,
    _parse_required_date,
    _publish,
    _raise_bad_request_from_exception,
    _read_json_object,
    _require_record,
    _resolve_default_class_id_for_user,
    _serialize_record,
    _validate_payload,
)

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_v1_bp.get("/health")
# Intentionally unauthenticated for liveness/readiness checks; rate limiting will follow.
def health():
    """Service heartbeat endpoint for deployment/readiness checks."""
    _publish("api.health_checked")
    return jsonify(
        {"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")}
    )
