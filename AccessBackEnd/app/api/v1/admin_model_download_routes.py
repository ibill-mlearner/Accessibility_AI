from __future__ import annotations

from flask import jsonify

from .routes import api_v1_bp
from ...api.errors import BadRequestError
from ...schemas.validation import AdminModelDownloadPayloadSchema
from ...utils.api_checker import _enforce_roles, _read_json_object, _validate_payload


@api_v1_bp.post('/admin/model-downloads')
def submit_admin_model_download_request_v1():
    denied = _enforce_roles('admin')
    if denied is not None:
        return denied

    payload = _read_json_object()

    try:
        validated_payload = _validate_payload(payload, AdminModelDownloadPayloadSchema())
        model_id = validated_payload.get('model_id')
    except BadRequestError as exc:
        return jsonify({
            "error": "invalid model_id payload; Marshmallow validation failed",
            "details": getattr(exc, "details", {}),
        }), 400

    return jsonify({
        "ok": True,
        "message": "Hey, you reached me.",
        "model_id": model_id,
        "status": "queued_stub"
    }), 200
