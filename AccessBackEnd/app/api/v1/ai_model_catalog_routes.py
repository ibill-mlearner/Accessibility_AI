from typing import Any
import time

from flask import current_app, jsonify, session, request
from flask_login import current_user, login_required
from .routes import _read_json_object, api_v1_bp
from ...services.ai_pipeline.model_reconciliation import AIModelReconciliationService
from ...services.ai_pipeline_v2.interfaces import AIPipelineServiceInterface
from ...services.ai_pipeline_v2.model_selection import ModelSelectionError, resolve_provider_model_selection
from ...models import AIModel
from ...extensions import db

AI_CATALOG_TTL_SECONDS = 30
_ai_catalog_cache: dict[tuple[int | None, Any], dict[str, Any]] = {}



def _extract_available_model_ids(payload: dict[str, Any]) -> dict[str, set[str]]:
    provider_models: dict[str, set[str]] = {"ollama": set(), "huggingface": set()}
    for provider, top_key in (("ollama", "ollama"), ("huggingface", "huggingface_local")):
        provider_payload = payload.get(top_key)
        if not isinstance(provider_payload, dict):
            continue
        models = provider_payload.get("models")
        if not isinstance(models, list):
            continue
        for model in models:
            if isinstance(model, dict) and model.get("id"):
                provider_models[provider].add(str(model.get("id")).strip().lower())
    return provider_models


def _catalog_cache_key() -> tuple[int | None, Any]:
    user_id = int(current_user.id) if getattr(current_user, 'is_authenticated', False) else None
    return user_id, session.get('auth_session_id')


def _invalidate_ai_catalog_cache() -> None:
    _ai_catalog_cache.pop(_catalog_cache_key(), None)


@api_v1_bp.get("/ai/models")
@login_required
def list_persisted_ai_models():
    include_live = str(request.args.get("include_live") or '').strip().lower() in {'1', 'true', 'yes'}
    reconcile = str(request.args.get('reconcile') or '').strip().lower() in {'1', 'true', 'yes'}
    ai_service: AIPipelineServiceInterface = current_app.extensions['ai_service']
    if reconcile:
        AIModelReconciliationService(ai_service).reconcile()

    availability: dict[tuple[str, str], bool] = {}
    if include_live:
        inventory = ai_service.list_available_models()
        available_by_provider = _extract_available_model_ids(inventory)
        availability = {
            (provider, model_id.lower()): True
            for provider, model_ids in available_by_provider.items()
            for model_id in model_ids
        }
    records = (
        db.session.query(AIModel)
        .order_by(AIModel.provider.asc(), AIModel.model_id.asc())
        .all()
    )
    response = []

    for model in records:
        payload = {
            "id": model.id,
            "provider": model.provider,
            "model_id": model.model_id,
            "source": model.source,
            "path": model.path,
            "active": model.active,
            "last_seen_at": model.last_seen_at.isoformat() if model.last_seen_at else None,
        }
        if include_live:
            payload['available_live'] = availability.get(
                (model.provider, model.model_id.lower()),
                False
            )
        response.append(payload)

    return jsonify(
        {
            "models": response,
            "count": len(response)
        }
    ), 200


@api_v1_bp.get("/ai/models/available")
@login_required
def list_available_ai_models():
    """Return read-only inventory of currently discoverable AI models."""
    ai_service: AIPipelineServiceInterface = current_app.extensions["ai_service"]
    payload = ai_service.list_available_models()
    return jsonify(payload), 200


@api_v1_bp.get("/ai/catalog")
@login_required
def get_ai_catalog():
    """Return discoverable models grouped by provider, with temporary legacy fields."""
    include_health = str(request.args.get('include_health') or '').strip().lower() in {'1', 'true', 'yes'}
    ai_service: AIPipelineServiceInterface = current_app.extensions["ai_service"]

    cache_key = _catalog_cache_key()
    now = time.time()
    cached = _ai_catalog_cache.get(cache_key)

    span_start = time.perf_counter()
    span: dict[str, Any] = {"cache_hit": False}

    if cached and (now - cached['timestamp']) < AI_CATALOG_TTL_SECONDS:
        span["cache_hit"] = True
        response_payload = cached["payload"]
    else:
        inventory_start = time.perf_counter()
        inventory = ai_service.list_available_models()
        span["inventory_ms"] = round((time.perf_counter() - inventory_start) * 1000, 2)

        provider_grouped = {
            "ollama": sorted([m for m in inventory.get("ollama", {}).get("models", []) if isinstance(m, dict)], key=lambda item: str(item.get("id") or "")),
            "huggingface": sorted([m for m in inventory.get("huggingface_local", {}).get("models", []) if isinstance(m, dict)], key=lambda item: str(item.get("id") or "")),
        }
        flat_models = [
            {"provider": provider, **model}
            for provider, models in provider_grouped.items()
            for model in models
        ]

        try:
            selected = resolve_provider_model_selection({}, ai_service, inventory_payload=inventory)
        except ModelSelectionError as exc:
            return jsonify(exc.payload), exc.status_code

        response_payload = {
            "selected": selected,
            "models_by_provider": provider_grouped,
            "models": flat_models,
            # Temporary legacy field retained for frontend compatibility.
            "families": [],
        }
        _ai_catalog_cache[cache_key] = {
            'payload': response_payload,
            'timestamp': now,
        }

    if include_health:
        provider_health = ai_service.provider_health() if hasattr(ai_service, 'provider_health') else {}
        response_payload['provider_health'] = provider_health

    span["total_ms"] = round((time.perf_counter() - span_start) * 1000, 2)
    response_payload.setdefault("meta", {})["timings_ms"] = span

    return jsonify(response_payload), 200


@api_v1_bp.post('/ai/selection')
@login_required
def set_ai_selection():
    """Persist per-session AI model selection for the authenticated user."""
    payload = _read_json_object()
    ai_service: AIPipelineServiceInterface = current_app.extensions["ai_service"]

    try:
        selected = resolve_provider_model_selection(payload, ai_service, allow_session=False, require_explicit=True)
    except ModelSelectionError as exc:
        return jsonify(exc.payload), exc.status_code

    session["ai_model_selection"] = {
        "user_id": int(current_user.id),
        "auth_session_id": session.get("auth_session_id"),
        "provider": selected["provider"],
        "model_id": selected["model_id"],
    }
    _invalidate_ai_catalog_cache()

    return jsonify(
        {
            "provider": selected["provider"],
            "model_id": selected["model_id"],
            "source": selected["source"],
        }
    ), 200
