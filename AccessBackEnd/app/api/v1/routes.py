from __future__ import annotations

from copy import deepcopy
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from ..errors import BadRequestError, NotFoundError
from .api_view import register_api_view_route

from ...logging_config import DomainEvent


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


_RESOURCE_STORE: dict[str, list[dict[str, Any]]] = {
    "chats": [
        {
            "id": 1,
            "title": "Bio 103 lecture recap",
            "start": "2026-02-09T09:00:00Z",
            "model": "gpt-4o-mini",
            "class": "Biology 103",
            "user": "student_1",
        },
        {
            "id": 2,
            "title": "CS 101 study session",
            "start": "2026-02-09T10:30:00Z",
            "model": "gpt-4o-mini",
            "class": "Computer Science 101",
            "user": "student_2",
        },
    ],
    "messages": [
        {
            "id": 1,
            "chat_id": 1,
            "message_text": "Can you summarize mitochondria function?",
            "vote": "good",
            "note": "yes",
            "help_intent": "summarization",
        },
        {
            "id": 2,
            "chat_id": 1,
            "message_text": "Mitochondria generate ATP for cell energy.",
            "vote": "good",
            "note": "no",
            "help_intent": "note_taking",
        },
        {
            "id": 3,
            "chat_id": 2,
            "message_text": "Explain recursion with an example.",
            "vote": "bad",
            "note": "yes",
            "help_intent": "restating",
        },
    ],
    "features": [
        {
            "id": 1,
            "title": "Note Taking assistance",
            "description": "Responses set to assist with taking notes for selected class",
            "enabled": True,
            "instructor_id": 4,
            "class_id": 1,
        },
        {
            "id": 2,
            "title": "Summarization and restating",
            "description": "Responses focused on summaries and restatements",
            "enabled": False,
            "instructor_id": 5,
            "class_id": 2,
        },
        {
            "id": 3,
            "title": "Text-to-speech formatting",
            "description": "Responses expected to supply Text-to-speech features",
            "enabled": False,
            "instructor_id": 6,
            "class_id": 3,
        },
    ],
    "classes": [
        {
            "id": 1,
            "role": "student",
            "name": "Biology 103",
            "description": "Assist with a guided approach to class material or intent.",
        },
        {
            "id": 2,
            "role": "student",
            "name": "Computer Science 101",
            "description": "Assist with a guided approach to class material or intent.",
        },
        {
            "id": 3,
            "role": "student",
            "name": "CyberSecurity 230",
            "description": "Assist with a guided approach to class material or intent.",
        },
        {
            "id": 4,
            "role": "instructor",
            "name": "Biology 103",
            "description": "Assist with a guided approach with instructor prompts and controls.",
        },
        {
            "id": 5,
            "role": "instructor",
            "name": "Chemistry 213",
            "description": "Enable/disable prompt complexity and class-level controls.",
        },
        {
            "id": 6,
            "role": "instructor",
            "name": "Genetics 330",
            "description": "Enable/disable class files and upload settings.",
        },
    ],
    "notes": [
        {
            "id": 1,
            "class": "Bio",
            "date": "2026-02-09",
            "chat": "Chat 3",
            "content": "System's response . . .",
        },
        {
            "id": 2,
            "class": "Chem",
            "date": "2026-02-09",
            "chat": "Chat 2",
            "content": "User's prompt . . .",
        },
    ],
}


def _publish(event_name: str, payload: dict[str, Any] | None = None) -> None:
    """Publish a domain event for endpoint observability."""
    current_app.extensions["event_bus"].publish(DomainEvent(event_name, payload or {}))


def _list_resource(resource_name: str):
    """Return all records for a resource without data transformation."""
    records = _RESOURCE_STORE[resource_name]
    _publish(f"api.{resource_name}.listed", {"count": len(records)})
    return jsonify(deepcopy(records)), 200


def _get_resource(resource_name: str, record_id: int):
    """Return a single record by id; pass-through payload contract."""
    for record in _RESOURCE_STORE[resource_name]:
        if record.get("id") == record_id:
            _publish(f"api.{resource_name}.retrieved", {"id": record_id})
            return jsonify(deepcopy(record)), 200

    _resource_not_found(resource_name, record_id)


def _create_resource(resource_name: str):
    """Store the client payload as submitted and return it unchanged."""
    payload = _read_json_object()

    _RESOURCE_STORE[resource_name].append(payload)
    _publish(f"api.{resource_name}.created", {"has_id": "id" in payload})
    return jsonify(deepcopy(payload)), 201


def _update_resource(resource_name: str, record_id: int):
    """Replace a record with the provided payload without mutating fields."""
    payload = _read_json_object()

    records = _RESOURCE_STORE[resource_name]
    for index, record in enumerate(records):
        if record.get("id") == record_id:
            records[index] = payload
            _publish(f"api.{resource_name}.updated", {"id": record_id})
            return jsonify(deepcopy(payload)), 200

    _resource_not_found(resource_name, record_id)


def _delete_resource(resource_name: str, record_id: int):
    """Delete a record by id and return a minimal pass-through status."""
    records = _RESOURCE_STORE[resource_name]
    for index, record in enumerate(records):
        if record.get("id") == record_id:
            deleted = records.pop(index)
            _publish(f"api.{resource_name}.deleted", {"id": record_id})
            return jsonify(deepcopy(deleted)), 200

    _resource_not_found(resource_name, record_id)


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

    initiated_by = "anonymous"
    if getattr(current_user, "is_authenticated", False):
        initiated_by = str(current_user.get_id() or getattr(current_user, "email", "authenticated_user"))
    elif payload.get("user"):
        initiated_by = str(payload["user"])
    elif payload.get("user_id"):
        initiated_by = str(payload["user_id"])

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

    return jsonify(result), 200


register_api_view_route(api_v1_bp)

for _resource in ("chats", "messages", "classes", "notes", "features"):
    _register_resource_routes(_resource)
