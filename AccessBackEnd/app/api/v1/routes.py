from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from ..errors import BadRequestError, NotFoundError
from .api_view import register_api_view_route

from ...db.repositories.interaction_repo import AIInteractionRepository
from ...extensions import db
from ...logging_config import DomainEvent
from ...models import AIInteraction, Chat, CourseClass, Feature, Message, Note


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


# ---------------------------------------------------------------------------
# Temporary pass-through storage for endpoint-validation sprint.
# Logic intent:
# - Keep response shapes stable while frontend/backend contracts are wired.
# - Store records as submitted without API-level transformation.
# - Replace this with repository/database integration in a later sprint.
# ---------------------------------------------------------------------------

_RESOURCE_SINGULAR_NAME: dict[str, str] = {
    "chats": "chat",
    "messages": "message",
    "classes": "class",
    "notes": "note",
    "features": "feature",
}


def _resource_not_found(resource_name: str, record_id: int):
    """Raise standardized 404 for missing resource records."""
    raise NotFoundError(
        f"{_RESOURCE_SINGULAR_NAME.get(resource_name, 'resource')} not found",
        details={"resource": resource_name, "id": record_id},
    )


def _read_json_object() -> dict[str, Any]:
    """Read request JSON body and require object payloads for CRUD routes."""
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequestError("json body required")
    if not isinstance(payload, dict):
        raise BadRequestError("json object body required")
    return payload


_RESOURCE_MODEL_MAP: dict[str, type] = {
    "chats": Chat,
    "messages": Message,
    "classes": CourseClass,
    "notes": Note,
    "features": Feature,
}

_RESOURCE_API_TO_MODEL_FIELDS: dict[str, dict[str, str]] = {
    "chats": {"start": "started_at", "class": "class_id", "user": "user_id"},
    "notes": {"date": "noted_on", "class": "class_id"},
}

_RESOURCE_MODEL_TO_API_FIELDS: dict[str, dict[str, str]] = {
    name: {model_field: api_field for api_field, model_field in field_map.items()}
    for name, field_map in _RESOURCE_API_TO_MODEL_FIELDS.items()
}


def _coerce_field_value(resource_name: str, model_field: str, value: Any) -> Any:
    if value is None:
        return None

    if resource_name == "chats" and model_field == "started_at" and isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise BadRequestError("invalid datetime format for start") from exc

    if resource_name == "notes" and model_field == "noted_on" and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise BadRequestError("invalid date format for date") from exc

    return value


def _resource_model(resource_name: str):
    return _RESOURCE_MODEL_MAP[resource_name]


def _deserialize_payload(resource_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    model = _resource_model(resource_name)
    valid_model_fields = {column.name for column in model.__table__.columns}
    field_map = _RESOURCE_API_TO_MODEL_FIELDS.get(resource_name, {})

    transformed: dict[str, Any] = {}
    for api_field, value in payload.items():
        model_field = field_map.get(api_field, api_field)
        if model_field not in valid_model_fields:
            raise BadRequestError(f"unknown field: {api_field}")
        transformed[model_field] = _coerce_field_value(resource_name, model_field, value)
    return transformed


def _serialize_record(resource_name: str, record: Any) -> dict[str, Any]:
    model_to_api = _RESOURCE_MODEL_TO_API_FIELDS.get(resource_name, {})
    payload: dict[str, Any] = {}

    for column in record.__table__.columns:
        model_field = column.name
        api_field = model_to_api.get(model_field, model_field)
        value = getattr(record, model_field)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        payload[api_field] = value

    return payload


def _publish(event_name: str, payload: dict[str, Any] | None = None) -> None:
    """Publish a domain event for endpoint observability."""
    current_app.extensions["event_bus"].publish(DomainEvent(event_name, payload or {}))


def _extract_response_text(result: Any) -> str:
    """Normalize provider payload into a storable interaction response string."""
    if isinstance(result, dict):
        for key in ("response_text", "response", "answer", "result"):
            value = result.get(key)
            if value is not None:
                return str(value)

        if "data" in result:
            data_value = result["data"]
            if isinstance(data_value, str):
                return data_value
            if data_value is not None:
                return json.dumps(data_value, default=str)

    if isinstance(result, str):
        return result

    return json.dumps(result, default=str)




def _resolve_initiated_by(payload: dict[str, Any]) -> str:
    """Resolve actor identifier used for AI interaction auditing."""
    if getattr(current_user, "is_authenticated", False):
        return str(current_user.get_id() or getattr(current_user, "email", "authenticated_user"))
    if payload.get("user"):
        return str(payload["user"])
    if payload.get("user_id"):
        return str(payload["user_id"])
    return "anonymous"


def _resolve_provider(result: Any) -> str:
    """Resolve persisted provider name from response payload or app config."""
    provider = current_app.config.get("AI_PROVIDER") or "unknown"
    if isinstance(result, dict):
        meta_payload = result.get("meta")
        if isinstance(meta_payload, dict) and meta_payload.get("provider"):
            return str(meta_payload["provider"])
        if result.get("provider"):
            return str(result["provider"])
    return str(provider)


def _resolve_chat_id(payload: dict[str, Any]) -> int | None:
    """Extract optional chat id and validate integer shape when present."""
    chat_id = payload.get("chat_id")
    if chat_id is None:
        return None
    try:
        return int(chat_id)
    except (TypeError, ValueError) as exc:
        raise BadRequestError("chat_id must be an integer") from exc


def _persist_ai_interaction(payload: dict[str, Any], prompt: str, result: Any) -> tuple[Any, int] | None:
    """Persist an AI interaction; return error response tuple when persistence fails."""
    interaction_repo = AIInteractionRepository(AIInteraction)

    try:
        interaction_repo.create(
            db.session,
            prompt=prompt,
            response_text=_extract_response_text(result),
            provider=_resolve_provider(result),
            chat_id=_resolve_chat_id(payload),
        )
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": {
                        "code": "persistence_error",
                        "message": "Failed to persist AI interaction",
                        "details": {"exception": exc.__class__.__name__},
                    }
                }
            ),
            500,
        )

    return None

def _list_resource(resource_name: str):
    """Return all records for a resource from ORM-backed storage."""
    model = _resource_model(resource_name)
    records = db.session.query(model).all()
    _publish(f"api.{resource_name}.listed", {"count": len(records)})
    return jsonify([_serialize_record(resource_name, record) for record in records]), 200


def _get_resource(resource_name: str, record_id: int):
    """Return a single ORM record by primary key."""
    model = _resource_model(resource_name)
    record = db.session.get(model, record_id)
    if record is None:
        _resource_not_found(resource_name, record_id)

    _publish(f"api.{resource_name}.retrieved", {"id": record_id})
    return jsonify(_serialize_record(resource_name, record)), 200


def _create_resource(resource_name: str):
    """Create and persist a resource record from API payload fields."""
    payload = _read_json_object()
    model = _resource_model(resource_name)
    transformed_payload = _deserialize_payload(resource_name, payload)

    record = model(**transformed_payload)
    db.session.add(record)
    db.session.commit()
    _publish(f"api.{resource_name}.created", {"has_id": "id" in payload})
    return jsonify(_serialize_record(resource_name, record)), 201


def _update_resource(resource_name: str, record_id: int):
    """Update an existing ORM-backed resource from API payload fields."""
    payload = _read_json_object()
    model = _resource_model(resource_name)
    record = db.session.get(model, record_id)
    if record is None:
        _resource_not_found(resource_name, record_id)

    transformed_payload = _deserialize_payload(resource_name, payload)
    for field_name, value in transformed_payload.items():
        setattr(record, field_name, value)

    db.session.commit()
    _publish(f"api.{resource_name}.updated", {"id": record_id})
    return jsonify(_serialize_record(resource_name, record)), 200


def _delete_resource(resource_name: str, record_id: int):
    """Delete a persisted resource by id and return the deleted payload."""
    model = _resource_model(resource_name)
    record = db.session.get(model, record_id)
    if record is None:
        _resource_not_found(resource_name, record_id)

    deleted_payload = _serialize_record(resource_name, record)
    db.session.delete(record)
    db.session.commit()
    _publish(f"api.{resource_name}.deleted", {"id": record_id})
    return jsonify(deleted_payload), 200


def _register_resource_routes(resource_name: str) -> None:
    """Register standard CRUD endpoints for a top-level API resource."""

    @login_required
    def list_handler() -> tuple[Any, int]:
        return _list_resource(resource_name)

    @login_required
    def create_handler() -> tuple[Any, int]:
        return _create_resource(resource_name)

    @login_required
    def get_handler(record_id: int) -> tuple[Any, int]:
        return _get_resource(resource_name, record_id)

    @login_required
    def update_handler(record_id: int) -> tuple[Any, int]:
        return _update_resource(resource_name, record_id)

    @login_required
    def delete_handler(record_id: int) -> tuple[Any, int]:
        return _delete_resource(resource_name, record_id)

    api_v1_bp.add_url_rule(f"/{resource_name}", endpoint=f"list_{resource_name}", view_func=list_handler, methods=["GET"])
    api_v1_bp.add_url_rule(
        f"/{resource_name}", endpoint=f"create_{resource_name}", view_func=create_handler, methods=["POST"]
    )
    api_v1_bp.add_url_rule(
        f"/{resource_name}/<int:record_id>",
        endpoint=f"get_{resource_name}_item",
        view_func=get_handler,
        methods=["GET"],
    )
    api_v1_bp.add_url_rule(
        f"/{resource_name}/<int:record_id>",
        endpoint=f"update_{resource_name}_item",
        view_func=update_handler,
        methods=["PUT", "PATCH"],
    )
    api_v1_bp.add_url_rule(
        f"/{resource_name}/<int:record_id>",
        endpoint=f"delete_{resource_name}_item",
        view_func=delete_handler,
        methods=["DELETE"],
    )


@api_v1_bp.get("/health")
@login_required
def health():
    """Service heartbeat endpoint for deployment/readiness checks."""
    _publish("api.health_checked")
    return jsonify({"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")})


@api_v1_bp.post("/ai/interactions")
def create_ai_interaction():
    """Run a single AI interaction.

    Logic intent:
    - Accept client payload in a pass-through shape.
    - Support future growth keys (``system_prompt`` and ``rag``) without blocking requests.
    - Forward only currently supported fields to the AI service for this sprint.
    - Return provider output without API-level reshaping.
    """
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt") or ""

    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_system_prompt": bool(payload.get("system_prompt")),
            "has_rag": bool(payload.get("rag")),
        },
    )

    initiated_by = _resolve_initiated_by(payload)

    try:
        result = current_app.extensions["ai_service"].run_interaction(
            prompt=prompt,
            context=payload.get("context"),
            initiated_by=initiated_by,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        return jsonify({"error": {"code": "upstream_error", "message": str(exc), "details": {}}}), 502

    persistence_error = _persist_ai_interaction(payload, prompt, result)
    if persistence_error is not None:
        return persistence_error

    return jsonify(result), 200


register_api_view_route(api_v1_bp)

for _resource in ("chats", "messages", "classes", "notes", "features"):
    _register_resource_routes(_resource)
