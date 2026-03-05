from typing import Any

from flask import current_app, jsonify, session
from flask_login import current_user, login_required

from ...helpers.ai_interaction_helpers import (
    _extract_available_model_ids,
    _resolve_selected_model,
    resolve_model_selection,
)
from .routes import BadRequestError, _read_json_object, api_v1_bp
from ...services.ai_pipeline.model_catelog import MODEL_FAMILIES, family_id_from_model_id


@api_v1_bp.get("/ai/models/available")
@login_required
def list_available_ai_models():
    """Return read-only inventory of currently discoverable AI models."""
    ai_service = current_app.extensions["ai_service"]
    payload = ai_service.list_available_models()
    return jsonify(payload), 200


@api_v1_bp.get("/ai/catalog")
@login_required
def get_ai_catalog():
    """Return catalog grouped by model family with discoverability and current selection."""
    ai_service = current_app.extensions["ai_service"]
    inventory = ai_service.list_available_models()
    available_by_provider = _extract_available_model_ids(inventory)

    families: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        models: list[dict[str, Any]] = []
        for provider, candidates in family.provider_candidates.items():
            for model_id in candidates:
                models.append(
                    {
                        "provider": provider,
                        "model_id": model_id,
                        "available": model_id.lower() in available_by_provider.get(provider, set()),
                    }
                )
        families.append(
            {
                "family_id": family.family_id,
                "label": family.label,
                "owner": family.owner,
                "models": models,
            }
        )

    response_payload = {
        "families": families,
        "selected": _resolve_selected_model(inventory),
    }
    return jsonify(response_payload), 200


@api_v1_bp.post('/ai/selection')
@login_required
def set_ai_selection():
    """Persist per-session AI model selection for the authenticated user."""
    payload = _read_json_object()
    ai_service = current_app.extensions["ai_service"]
    inventory = ai_service.list_available_models()
    available_by_provider = _extract_available_model_ids(inventory)

    has_provider_pair = bool(payload.get("provider") and payload.get("model_id"))
    has_family_pair = bool(payload.get("family_id") and payload.get("provider_preference"))
    if has_provider_pair == has_family_pair:
        raise BadRequestError(
            "Provide either provider/model_id or family_id/provider_preference",
        )

    try:
        if has_provider_pair:
            selected = resolve_model_selection(
                provider=str(payload.get("provider") or "").strip().lower(),
                model_id=str(payload.get("model_id") or "").strip(),
                available_model_ids=available_by_provider,
            )
        else:
            selected = resolve_model_selection(
                family_id=str(payload.get("family_id") or "").strip(),
                provider_preference=str(payload.get("provider_preference") or "").strip().lower(),
                available_model_ids=available_by_provider,
            )
    except ValueError as exc:
        err_msg = str(exc)
        if "No candidate model available" in err_msg:
            return jsonify({"error": "no available model for requested family"}), 400
        raise BadRequestError(err_msg) from exc

    session["ai_model_selection"] = {
        "user_id": int(current_user.id),
        "auth_session_id": session.get("auth_session_id"),
        "provider": selected["provider"],
        "model_id": selected["model_id"],
    }

    return jsonify(
        {
            "provider": selected["provider"],
            "model_id": selected["model_id"],
            "family_id": family_id_from_model_id(selected["model_id"]),
        }
    ), 200
