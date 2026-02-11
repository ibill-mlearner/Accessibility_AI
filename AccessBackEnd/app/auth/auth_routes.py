from __future__ import annotations

from flask import Blueprint, jsonify, request

from .auth_methods import (
    AuthService,
    DuplicateIdentityError,
    InvalidCredentialsError,
    ValidationError,
)


def create_auth_blueprint(auth_service: AuthService, url_prefix: str = "/auth") -> Blueprint:
    """Create a framework adapter around the standalone auth service."""

    auth_bp = Blueprint("standalone_auth", __name__, url_prefix=url_prefix)

    @auth_bp.post("/register")
    def register() -> tuple[object, int]:
        payload = request.get_json(silent=True) or {}
        identifier = payload.get("identifier")
        password = payload.get("password")

        try:
            user = auth_service.register(identifier=identifier, password=password)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400
        except DuplicateIdentityError as exc:
            return jsonify({"error": str(exc)}), 409

        return (
            jsonify(
                {
                    "id": user.user_id,
                    "identifier": user.identifier,
                    "created_at": user.created_at.isoformat(),
                }
            ),
            201,
        )

    @auth_bp.post("/login")
    def login() -> tuple[object, int]:
        payload = request.get_json(silent=True) or {}
        identifier = payload.get("identifier")
        password = payload.get("password")

        try:
            user, token = auth_service.login(identifier=identifier, password=password)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400
        except InvalidCredentialsError as exc:
            return jsonify({"error": str(exc)}), 401

        return jsonify({"token": token, "user": {"id": user.user_id, "identifier": user.identifier}}), 200

    @auth_bp.get("/verify")
    def verify() -> tuple[object, int]:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer", "", 1).strip() if auth_header else ""

        try:
            claims = auth_service.verify_access_token(token)
        except InvalidCredentialsError as exc:
            return jsonify({"error": str(exc)}), 401

        return jsonify({"claims": claims}), 200

    return auth_bp
