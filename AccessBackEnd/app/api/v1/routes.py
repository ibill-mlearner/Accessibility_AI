from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from ..errors import BadRequestError
from .api_view import register_api_view_route

from ...db.repositories.interaction_repo import AIInteractionRepository
from ...extensions import db
from ...models import AIInteraction
from ...services.logging import DomainEvent

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _publish(event_name: str, payload: dict[str, Any] | None = None) -> None:
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


def _todo_response(
    *,
    endpoint: str,
    next_steps: list[str],
    payload: dict[str, Any] | None = None,
    status_code: int = 501,
):
    """Return explicit placeholder output for handlers that are intentionally unimplemented."""
    return (
        jsonify(
            {
                "message": "TODO: implement",
                "endpoint": endpoint,
                "next_steps": next_steps,
                "payload": payload or {},
            }
        ),
        status_code,
    )


@api_v1_bp.post("/auth/register")
def register_auth_user():
    """Placeholder for API-v1 user registration flow."""
    payload = _read_json_object()

    # TODO(register):
    # 1) Validate request contract (required fields, email format, password policy).
    # 2) Authorize registration path (invite-only checks / tenant constraints as needed).
    # 3) Persist user credentials/profile via auth domain services and emit audit events.
    # 4) Return normalized auth tokens + user envelope.
    return _todo_response(
        endpoint="POST /api/v1/auth/register",
        next_steps=[
            "validate_register_payload",
            "authorize_registration_context",
            "persist_user_and_issue_tokens",
        ],
        payload={"received_keys": sorted(payload.keys())},
    )


@api_v1_bp.post("/auth/login")
def login_auth_user():
    """Placeholder for API-v1 login flow."""
    payload = _read_json_object()

    # TODO(login):
    # 1) Validate login payload (identifier/password shape, required fields).
    # 2) Authorize login attempt (account status, lockouts, MFA preconditions).
    # 3) Persist session/token metadata and security audit log entries.
    # 4) Return auth/session envelope expected by frontend.
    return _todo_response(
        endpoint="POST /api/v1/auth/login",
        next_steps=[
            "validate_login_payload",
            "authorize_login_attempt",
            "persist_session_and_audit",
        ],
        payload={"received_keys": sorted(payload.keys())},
    )


@api_v1_bp.get("/chats")
@login_required
def list_chats():
    """Placeholder for listing chats accessible to the current user."""
    # TODO(chats.list):
    # 1) Validate query contract (pagination/cursor/filter fields).
    # 2) Authorize user scope (owner, instructor, enrollment visibility).
    # 3) Persist/read sequence: fetch chat summaries from repository with stable ordering.
    # 4) Return paginated chat collection envelope.
    return _todo_response(
        endpoint="GET /api/v1/chats",
        next_steps=[
            "validate_chat_list_query",
            "authorize_chat_list_scope",
            "read_chat_collection",
        ],
        payload={"user_id": current_user.get_id()},
    )


@api_v1_bp.post("/chats")
@login_required
def create_chat():
    """Placeholder for creating a chat within class/user scope."""
    payload = _read_json_object()

    # TODO(chats.create):
    # 1) Validate payload contract (class_id/title/model and defaults).
    # 2) Authorize creation scope (owner self-write + enrollment/instructor permissions).
    # 3) Persist chat row and creation metadata inside transaction boundaries.
    # 4) Return created chat response envelope.
    return _todo_response(
        endpoint="POST /api/v1/chats",
        next_steps=[
            "validate_chat_create_payload",
            "authorize_chat_create_scope",
            "persist_chat_record",
        ],
        payload={"received_keys": sorted(payload.keys())},
    )


@api_v1_bp.get("/chats/<int:chat_id>/messages")
@login_required
def list_chat_messages(chat_id: int):
    """Placeholder for listing messages in a chat visible to the current user."""
    # TODO(messages.list):
    # 1) Validate query contract (pagination, ordering, optional role filters).
    # 2) Authorize chat visibility (owner/instructor/enrollment checks against chat).
    # 3) Persist/read sequence: fetch ordered messages for chat_id from repository.
    # 4) Return message collection envelope with pagination metadata.
    return _todo_response(
        endpoint="GET /api/v1/chats/<chat_id>/messages",
        next_steps=[
            "validate_message_list_query",
            "authorize_message_list_scope",
            "read_message_collection",
        ],
        payload={"chat_id": chat_id, "user_id": current_user.get_id()},
    )


@api_v1_bp.post("/chats/<int:chat_id>/messages")
@login_required
def create_chat_message(chat_id: int):
    """Placeholder for creating a message in a chat."""
    payload = _read_json_object()

    # TODO(messages.create):
    # 1) Validate payload contract (message body/role/metadata fields).
    # 2) Authorize write scope (owner/instructor/enrollment checks for chat_id).
    # 3) Persist message row + optional side effects (intent/vote/note links) transactionally.
    # 4) Return created message envelope.
    return _todo_response(
        endpoint="POST /api/v1/chats/<chat_id>/messages",
        next_steps=[
            "validate_message_create_payload",
            "authorize_message_create_scope",
            "persist_message_record",
        ],
        payload={"chat_id": chat_id, "received_keys": sorted(payload.keys())},
    )


@api_v1_bp.get("/health")
@login_required
def health():
    """Service heartbeat endpoint for deployment/readiness checks."""
    _publish("api.health_checked")
    return jsonify(
        {"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")}
    )


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
        return str(
            current_user.get_id()
            or getattr(current_user, "email", "authenticated_user")
        )
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


def _persist_ai_interaction(
    payload: dict[str, Any], prompt: str, result: Any
) -> tuple[Any, int] | None:
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


@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    """Run a single AI interaction."""
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
        return (
            jsonify(
                {
                    "error": {
                        "code": "upstream_error",
                        "message": str(exc),
                        "details": {},
                    }
                }
            ),
            502,
        )

    persistence_error = _persist_ai_interaction(payload, prompt, result)
    if persistence_error is not None:
        return persistence_error

    return jsonify(result), 200


register_api_view_route(api_v1_bp)
