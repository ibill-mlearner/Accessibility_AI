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

    known_candidats_by_provider: dict[str, set[str]] = {
        "ollama": set(),
        "huggingface": set()
    }
    for family in MODEL_FAMILIES:
        for provider, candidates in family.provider_candidates.items():
            if provider not in known_candidats_by_provider:
                continue

            known_candidats_by_provider[provider].update(
                c.lower() for c in candidates
            )

    families: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        models: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()
        # seen_pairs = { EXAMPLE
        #     ("user", "gpt"),
        #     ("system", "gpt"),
        #     ("user", "llama")
        # }

        for provider, candidates in family.provider_candidates.items():
            available_models = available_by_provider.get(provider, set())
            for model_id in candidates:
                pair = (provider, model_id)
                if pair in seen_pairs:
                    continue
                models.append(
                    {
                        "provider": provider,
                        "model_id": model_id,
                        "available": model_id.lower() in available_models,
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

    uncataloged_models: list[dict[str, Any]] = []
    for provider in ('ollama', 'huggingface'):
        available_models = sorted(available_by_provider.get(provider, set()))
        known_models = known_candidats_by_provider[provider]
        for model_id in available_models:
            if model_id in known_models:
                continue
            uncataloged_models.append(
                {
                    "provider": provider,
                    'model_id': model_id,
                    'available': True
                }
            )

    if uncataloged_models:
        families.append(
            {
                'familiy_id': 'other_available',
                'label': 'other available models',
                'owner': 'discovered',
                'models': uncataloged_models
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
