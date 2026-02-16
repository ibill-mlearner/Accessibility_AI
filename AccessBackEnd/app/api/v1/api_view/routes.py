from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, render_template, request, session
from flask_login import login_user

from ....logging_config import DomainEvent
from ....models import User


_ENDPOINT_COMPONENTS: list[str] = [
    "api_view/endpoints/login.html",
    "api_view/endpoints/health.html",
    "api_view/endpoints/ai_interactions.html",
    "api_view/endpoints/chats_collection.html",
    "api_view/endpoints/chats_item.html",
    "api_view/endpoints/messages_collection.html",
    "api_view/endpoints/messages_item.html",
    "api_view/endpoints/classes_collection.html",
    "api_view/endpoints/classes_item.html",
    "api_view/endpoints/features_collection.html",
    "api_view/endpoints/features_item.html",
    "api_view/endpoints/notes_collection.html",
    "api_view/endpoints/notes_item.html",
    "api_view/endpoints/api_view.html",
]


def _current_session_token() -> str | None:
    """Return the signed Flask session payload token for the current request."""
    serializer = current_app.session_interface.get_signing_serializer(current_app)
    if serializer is None:
        return None
    return serializer.dumps(dict(session))


def login() -> tuple[Response, int]:
    """Authenticate a user and expose the signed session token for API view testing."""
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    login_user(user)
    session_token = _current_session_token()

    current_app.extensions["event_bus"].publish(
        DomainEvent("api.view_login_succeeded", {"user_id": user.id, "email": user.email})
    )

    return (
        jsonify(
            {
                "message": "login successful",
                "user": {"id": user.id, "email": user.email},
                "session_token": session_token,
            }
        ),
        200,
    )


def api_view() -> Response:
    """Render a template-based built-in API test page for v1 endpoints."""
    current_app.extensions["event_bus"].publish(DomainEvent("api.viewed"))
    return Response(render_template("api_view/index.html", endpoint_components=_ENDPOINT_COMPONENTS), mimetype="text/html")


def register_api_view_route(api_v1_bp: Blueprint) -> None:
    """Attach the standalone API view route to the v1 blueprint."""
    api_v1_bp.add_url_rule("/api_view", endpoint="api_view", view_func=api_view, methods=["GET"])
    api_v1_bp.add_url_rule("/api_view/login", endpoint="api_view_login", view_func=login, methods=["POST"])
