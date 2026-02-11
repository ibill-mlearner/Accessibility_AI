from __future__ import annotations

from flask import Blueprint, jsonify, request

from .auth_methods import AuthError, AuthService, AuthUser


def _user_payload(user: AuthUser) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}


def _bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip() or None


def create_auth_blueprint(auth_service: AuthService, *, name: str = "auth", url_prefix: str = "/auth") -> Blueprint:
    """Factory for an auth blueprint that can be mounted in any Flask app."""

    auth_bp = Blueprint(name, __name__, url_prefix=url_prefix)

    @auth_bp.errorhandler(AuthError)
    def handle_auth_error(exc: AuthError):
        return jsonify({"error": {"code": exc.code, "message": str(exc)}}), exc.status_code

    @auth_bp.post("/register")
    def register():
        payload = request.get_json(silent=True) or {}
        user = auth_service.register(
            email=payload.get("email", ""),
            password=payload.get("password", ""),
            role=payload.get("role", "student"),
        )
        return jsonify({"user": _user_payload(user)}), 201

    @auth_bp.post("/login")
    def login():
        payload = request.get_json(silent=True) or {}
        user, token = auth_service.login(
            email=payload.get("email", ""),
            password=payload.get("password", ""),
        )
        return jsonify({"message": "login successful", "token": token, "user": _user_payload(user)})

    @auth_bp.post("/logout")
    def logout():
        removed = auth_service.logout(_bearer_token())
        return jsonify({"message": "logout successful", "token_revoked": removed})

    @auth_bp.get("/me")
    def me():
        user = auth_service.validate_token(_bearer_token())
        if user is None:
            raise AuthError("auth token required", code="missing_token", status_code=401)
        return jsonify({"user": _user_payload(user)})

    return auth_bp
