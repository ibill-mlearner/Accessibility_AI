from typing import Any
import time

from flask import current_app, jsonify, session, request
from flask_login import current_user, login_required
from .routes import _read_json_object, api_v1_bp
from ...services.ai_pipeline.model_reconciliation import AIModelReconciliationService
from ...services.ai_pipeline_slim import AIPipelineServiceInterface
from ...services.ai_pipeline_v2.model_selection import (
    ModelSelectionError,
    normalize_model_id,
    resolve_catalog_selection,
    resolve_provider_model_selection,
)
from ...services.ai_pipeline_v2.inventory_extractors import extract_huggingface_model_id_map
from ...models import AIModel
from ...extensions import db

AI_CATALOG_TTL_SECONDS = 30
_ai_catalog_cache: dict[tuple[int | None, Any], dict[str, Any]] = {}


def _extract_available_model_ids(payload: dict[str, Any]) -> dict[str, set[str]]:
    return extract_huggingface_model_id_map(payload, normalize=normalize_model_id)


def _serialize_available_models_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Expose a stable public inventory contract for clients.
    Keep only fields needed by UI model pickers and hide backend internals
    (meta envelopes, runtime diagnostics, and provider-specific artifacts).
    During migration, map either local or legacy huggingface_local buckets.
    """
    model_defaults = payload.get("model_defaults") if isinstance(payload.get("model_defaults"), dict) else {}
    local_bucket = payload.get("local") if isinstance(payload.get("local"), dict) else {}
    legacy_bucket = payload.get("huggingface_local") if isinstance(payload.get("huggingface_local"), dict) else {}
    models_raw = local_bucket.get("models") if isinstance(local_bucket.get("models"), list) else legacy_bucket.get("models") if isinstance(legacy_bucket.get("models"), list) else []

    models = []
    for model in models_raw:
        if not isinstance(model, dict):
            continue
        model_id = str(model.get("id") or "").strip()
        if not model_id:
            continue
        models.append({"id": model_id})

    warnings = []
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    if isinstance(meta.get("warnings"), list):
        warnings = meta.get("warnings")

    return {
        "model_defaults": model_defaults,
        "local": {
            "models": models,
            "count": len(models),
        },
        "warnings": warnings,
    }


def _serialize_selected_selection(selected: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize selected-model payloads to one client-facing shape.
    Canonical key is `id`; `model_id` is emitted as a temporary alias
    so older clients keep working during the rollout window.
    """
    selected_provider = str((selected or {}).get("provider") or "").strip().lower()
    selected_id = str((selected or {}).get("id") or (selected or {}).get("model_id") or "").strip()
    source = str((selected or {}).get("source") or "").strip()
    return {
        "provider": selected_provider,
        "id": selected_id,
        # Deprecated alias kept during transition; remove in follow-up.
        "model_id": selected_id,
        "source": source,
    }


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
            (provider, normalize_model_id(model_id)): True
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
                (model.provider, normalize_model_id(model.model_id)),
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
    return jsonify(_serialize_available_models_payload(payload)), 200


@api_v1_bp.get("/ai/catalog")
@login_required
def get_ai_catalog():
    """Return persisted AI model catalog grouped by provider."""
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
        query_start = time.perf_counter()
        records = (
            db.session.query(AIModel)
            .filter(AIModel.active.is_(True))
            .order_by(AIModel.provider.asc(), AIModel.model_id.asc())
            .all()
        )
        if not records:
            records = (
                db.session.query(AIModel)
                .order_by(AIModel.provider.asc(), AIModel.model_id.asc())
                .all()
            )
        span["query_ms"] = round((time.perf_counter() - query_start) * 1000, 2)

        provider_grouped: dict[str, list[dict[str, Any]]] = {}
        ordered_models: list[dict[str, Any]] = []
        for record in records:
            provider = str(record.provider or "").strip().lower()
            model_payload = {
                "id": record.model_id,
                "source": record.source,
                "path": record.path,
                "active": bool(record.active),
            }
            provider_grouped.setdefault(provider, []).append(model_payload)
            ordered_models.append({"provider": provider, **model_payload})

        available_by_provider: dict[str, set[str]] = {
            provider: {normalize_model_id(str(model.get("id") or "")) for model in models if normalize_model_id(str(model.get("id") or ""))}
            for provider, models in provider_grouped.items()
        }

        selected = resolve_catalog_selection(
            persisted_selection=session.get("ai_model_selection") if isinstance(session.get("ai_model_selection"), dict) else None,
            active_user_id=int(current_user.id) if getattr(current_user, "is_authenticated", False) else None,
            active_session_id=session.get("auth_session_id"),
            config_provider=str(current_app.config.get("AI_PROVIDER") or "huggingface"),
            config_model_id=str(current_app.config.get("AI_MODEL_NAME") or ""),
            available_by_provider=available_by_provider,
            ordered_models=ordered_models,
        )

        response_payload = {
            "selected": _serialize_selected_selection(selected),
            "models_by_provider": provider_grouped,
            "models": ordered_models,
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

    response_payload["selected"] = _serialize_selected_selection(response_payload.get("selected") if isinstance(response_payload.get("selected"), dict) else {})

    span["total_ms"] = round((time.perf_counter() - span_start) * 1000, 2)
    response_payload.setdefault("meta", {})["timings_ms"] = span

    return jsonify(response_payload), 200


@api_v1_bp.post('/ai/selection')
@login_required
def set_ai_selection():
    """Persist the caller's model selection in session state for this user/session only.

    This endpoint does not mutate application config (`AI_PROVIDER`, `AI_MODEL_NAME`).
    If the product needs a true global pointer mutation, add a separate admin-only route
    rather than reusing `/api/v1/ai/selection`.
    """
    payload = _read_json_object()
    ai_service: AIPipelineServiceInterface = current_app.extensions["ai_service"]

    try:
        selected = resolve_provider_model_selection(payload, ai_service, allow_session=False, require_explicit=True)
    except ModelSelectionError as exc:
        return jsonify(exc.payload), exc.status_code

    # Store per-user/session override only; runtime config remains process-level and unchanged.
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
            "id": selected["model_id"],
            # Deprecated alias kept during transition; remove in follow-up.
            "model_id": selected["model_id"],
            "source": selected["source"],
        }
    ), 200
