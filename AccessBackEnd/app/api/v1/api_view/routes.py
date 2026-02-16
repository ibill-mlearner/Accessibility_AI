from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)
from flask_login import login_user, logout_user

from ....extensions import db
from ....models import User
from ....models.identity_defaults import build_transitional_identity_defaults
from ....services.logging import DomainEvent


_ALLOWED_ROLES = {"student", "instructor", "admin"}

_ENDPOINT_COMPONENTS: list[str] = [
    "api_view/endpoints/api_view.html",
    "api_view/endpoints/register.html",
    "api_view/endpoints/login.html",
    "api_view/endpoints/logout.html",
    "api_view/endpoints/auth_register.html",
    "api_view/endpoints/auth_login.html",
    "api_view/endpoints/chats_collection.html",
    "api_view/endpoints/chat_messages.html",
    "api_view/endpoints/health.html",
    "api_view/endpoints/ai_interactions.html",
]


def _current_session_token() -> str | None:
    """Return the signed Flask session payload token for the current request."""
    serializer = current_app.session_interface.get_signing_serializer(current_app)
    if serializer is None:
        return None
    return serializer.dumps(dict(session))


def register() -> tuple[Response, int]:
    """Create a new user account for API-view testing and return the session token."""
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "student").strip().lower()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if role not in _ALLOWED_ROLES:
        return (
            jsonify(
                {"error": f"role must be one of: {', '.join(sorted(_ALLOWED_ROLES))}"}
            ),
            400,
        )

    existing = User.query.filter_by(normalized_email=email).first()
    if existing is not None:
        return jsonify({"error": "email already registered"}), 409

    user = User(email=email, **build_transitional_identity_defaults(email))
    user.set_password(password)
    user.role = role
    db.session.add(user)
    db.session.commit()

    user.mark_login_success()
    login_user(user)
    db.session.commit()
    session_token = _current_session_token()

    current_app.extensions["event_bus"].publish(
        DomainEvent(
            "api.view_register_succeeded", {"user_id": user.id, "email": user.email}
        )
    )

    return (
        jsonify(
            {
                "message": "registration successful",
                "user": {"id": user.id, "email": user.email, "role": user.role},
                "session_token": session_token,
            }
        ),
        201,
    )


def login() -> tuple[Response, int]:
    """Authenticate a user and expose the signed session token for API view testing."""
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = User.query.filter_by(normalized_email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    user.mark_login_success()
    login_user(user)
    db.session.commit()
    session_token = _current_session_token()

    current_app.extensions["event_bus"].publish(
        DomainEvent(
            "api.view_login_succeeded", {"user_id": user.id, "email": user.email}
        )
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


def logout() -> tuple[Response, int]:
    """Clear the current auth session for API view testing flows."""
    logout_user()
    session.clear()

    current_app.extensions["event_bus"].publish(DomainEvent("api.view_logout_succeeded"))

    return jsonify({"message": "logout successful"}), 200


def api_view() -> Response:
    """Render a template-based built-in API test page for v1 endpoints."""
    current_app.extensions["event_bus"].publish(DomainEvent("api.viewed"))
    return Response(
        render_template(
            "api_view/index.html", endpoint_components=_ENDPOINT_COMPONENTS
        ),
        mimetype="text/html",
    )


def register_api_view_route(api_v1_bp: Blueprint) -> None:
    """Attach the standalone API view route to the v1 blueprint."""
    api_v1_bp.add_url_rule(
        "/api_view", endpoint="api_view", view_func=api_view, methods=["GET"]
    )
    api_v1_bp.add_url_rule(
        "/api_view/register",
        endpoint="api_view_register",
        view_func=register,
        methods=["POST"],
    )
    api_v1_bp.add_url_rule(
        "/api_view/login", endpoint="api_view_login", view_func=login, methods=["POST"]
    )
    api_v1_bp.add_url_rule(
        "/api_view/logout",
        endpoint="api_view_logout",
        view_func=logout,
        methods=["POST"],
    )
