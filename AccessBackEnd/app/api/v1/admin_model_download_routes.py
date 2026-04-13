from __future__ import annotations

from flask import current_app, jsonify

from .routes import api_v1_bp
from .ai_model_catalog_routes import _invalidate_ai_catalog_cache
from ...api.errors import BadRequestError
from ...schemas.validation import AdminModelDownloadPayloadSchema
from ...utils.api_checker import _enforce_roles, _read_json_object, _validate_payload
from ...utils.ai_checker import sync_ai_models_with_local_inventory


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

    ai_service = current_app.extensions.get("ai_service")
    download_result = None
    if ai_service is None or not hasattr(ai_service, "download_model"):
        return jsonify({
            "error": "ai_service not configured for model downloads",
            "details": {},
        }), 500

    try:
        download_result = ai_service.download_model(model_id)
        sync_ai_models_with_local_inventory(current_app)
        _invalidate_ai_catalog_cache()
    except Exception as exc:
        current_app.logger.warning("admin model download failed for model_id=%s: %s", model_id, exc)
        return jsonify({
            "error": "model download failed",
            "details": {"model_id": model_id},
        }), 502

    return jsonify({
        "ok": True,
        "message": "Model download attempted.",
        "model_id": model_id,
        "status": "downloaded",
        "download": download_result,
    }), 200
