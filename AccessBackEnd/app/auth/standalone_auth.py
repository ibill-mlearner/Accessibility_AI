from __future__ import annotations

from dataclasses import dataclass

from flask import Blueprint, jsonify, request

from .auth_methods import (
    AuthService,
    DuplicateIdentityError,
    InMemoryUserStore,
    InvalidCredentialsError,
    PBKDF2PasswordHasher,
    StatelessTokenManager,
    ValidationError,
)

_ALLOWED_ROLES = {"student", "instructor", "admin"}


@dataclass(frozen=True)
class StandaloneAuthRuntime:
    service: AuthService
    revoked_tokens: set[str]


def _extract_bearer_token(auth_header: str | None) -> str:
    if not auth_header:
        return ""
    return auth_header.replace("Bearer", "", 1).strip()


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def create_standalone_auth(
    *,
    url_prefix: str = "/auth",
    secret_key: str = "standalone-auth-secret",
    ttl_seconds: int = 3600,
) -> tuple[StandaloneAuthRuntime, Blueprint]:
    """Build an in-memory auth runtime plus Flask blueprint for standalone tests."""

    service = AuthService(
        user_store=InMemoryUserStore(),
        password_hasher=PBKDF2PasswordHasher(),
        token_manager=StatelessTokenManager(secret_key=secret_key, ttl_seconds=ttl_seconds),
    )
    revoked_tokens: set[str] = set()

    auth_bp = Blueprint("standalone_auth_v2", __name__, url_prefix=url_prefix)

    @auth_bp.post("/register")
    def register() -> tuple[object, int]:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error("invalid_payload", "json object body required", 400)

        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        role = (payload.get("role") or "student").strip().lower()

        if not email or not password:
            return _error("invalid_payload", "email and password are required", 400)
        if role not in _ALLOWED_ROLES:
            return _error("invalid_payload", "role must be student, instructor, or admin", 400)

        try:
            user = service.register(identifier=email, password=password)
        except ValidationError:
            return _error("invalid_payload", "email and password are required", 400)
        except DuplicateIdentityError:
            return _error("email_exists", "email already registered", 409)

        return jsonify({"user": {"id": user.user_id, "email": user.identifier, "role": role}}), 201

    @auth_bp.post("/login")
    def login() -> tuple[object, int]:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error("invalid_payload", "json object body required", 400)

        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""

        try:
            user, token = service.login(identifier=email, password=password)
        except (ValidationError, InvalidCredentialsError):
            return _error("invalid_credentials", "invalid credentials", 401)

        return jsonify({"token": token, "user": {"id": user.user_id, "email": user.identifier}}), 200

    @auth_bp.get("/me")
    def me() -> tuple[object, int]:
        token = _extract_bearer_token(request.headers.get("Authorization"))
        if not token or token in revoked_tokens:
            return _error("invalid_credentials", "invalid credentials", 401)

        try:
            claims = service.verify_access_token(token)
        except InvalidCredentialsError:
            return _error("invalid_credentials", "invalid credentials", 401)

        return jsonify({"user": {"id": claims["sub"], "email": claims["identifier"]}}), 200

    @auth_bp.post("/logout")
    def logout() -> tuple[object, int]:
        token = _extract_bearer_token(request.headers.get("Authorization"))
        if not token:
            return _error("invalid_credentials", "invalid credentials", 401)

        revoked_tokens.add(token)
        return jsonify({"token_revoked": True}), 200

    return StandaloneAuthRuntime(service=service, revoked_tokens=revoked_tokens), auth_bp
