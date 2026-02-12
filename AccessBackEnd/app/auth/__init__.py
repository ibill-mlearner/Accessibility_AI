from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .auth_methods import (
    AuthService,
    AuthUser,
    DuplicateIdentityError,
    InMemoryUserStore,
    InvalidCredentialsError,
    PBKDF2PasswordHasher,
    StatelessTokenManager,
    ValidationError,
)


def create_auth_blueprint(*args, **kwargs):
    from .auth_routes import create_auth_blueprint as _create_auth_blueprint

    return _create_auth_blueprint(*args, **kwargs)


@dataclass(frozen=True)
class StandaloneUser:
    user_id: str
    email: str
    password_hash: str
    role: str


class _StandaloneUserStore:
    def __init__(self) -> None:
        self._users_by_email: dict[str, StandaloneUser] = {}

    def get_by_email(self, email: str) -> StandaloneUser | None:
        return self._users_by_email.get(email)

    def create(self, email: str, password_hash: str, role: str) -> StandaloneUser:
        if email in self._users_by_email:
            raise DuplicateIdentityError("identity already exists")

        user = StandaloneUser(
            user_id=str(len(self._users_by_email) + 1),
            email=email,
            password_hash=password_hash,
            role=role,
        )
        self._users_by_email[email] = user
        return user


class _StandaloneAuthService:
    _ALLOWED_ROLES = {"student", "instructor", "admin"}

    def __init__(self) -> None:
        self.user_store = _StandaloneUserStore()
        self.password_hasher = PBKDF2PasswordHasher()
        self.token_manager = StatelessTokenManager(secret_key="standalone-auth-secret", ttl_seconds=3600)
        self.revoked_tokens: set[str] = set()

    @staticmethod
    def _normalize_email(email: str | None) -> str:
        return (email or "").strip().lower()

    def register(self, email: str | None, password: str | None, role: str | None) -> StandaloneUser:
        normalized_email = self._normalize_email(email)
        normalized_role = (role or "student").strip().lower()
        if not normalized_email or not password:
            raise ValidationError("email and password are required")
        if normalized_role not in self._ALLOWED_ROLES:
            raise ValidationError("invalid role")

        if self.user_store.get_by_email(normalized_email):
            raise DuplicateIdentityError("email already registered")

        password_hash = self.password_hasher.hash_password(password)
        return self.user_store.create(normalized_email, password_hash, normalized_role)

    def login(self, email: str | None, password: str | None) -> tuple[StandaloneUser, str]:
        normalized_email = self._normalize_email(email)
        user = self.user_store.get_by_email(normalized_email)
        if user is None or not self.password_hasher.verify_password(password or "", user.password_hash):
            raise InvalidCredentialsError("invalid credentials")

        auth_user = AuthUser(
            user_id=user.user_id,
            identifier=user.email,
            password_hash=user.password_hash,
            created_at=datetime.now(UTC),
        )
        token = self.token_manager.issue_token(auth_user)
        return user, token

    def me(self, token: str) -> StandaloneUser:
        if token in self.revoked_tokens:
            raise InvalidCredentialsError("token revoked")
        claims = self.token_manager.verify_token(token)
        email = self._normalize_email(str(claims.get("identifier", "")))
        user = self.user_store.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError("invalid credentials")
        return user

    def logout(self, token: str) -> None:
        self.token_manager.verify_token(token)
        self.revoked_tokens.add(token)


def create_standalone_auth(url_prefix: str = "/auth"):
    from flask import Blueprint, jsonify, request

    service = _StandaloneAuthService()
    auth_bp = Blueprint("standalone_auth_v2", __name__, url_prefix=url_prefix)

    @auth_bp.post("/register")
    def register():
        payload = request.get_json(silent=True) or {}
        try:
            user = service.register(payload.get("email"), payload.get("password"), payload.get("role"))
        except ValidationError:
            return jsonify({"error": {"code": "invalid_payload"}}), 400
        except DuplicateIdentityError:
            return jsonify({"error": {"code": "email_exists"}}), 409

        return jsonify({"user": {"id": user.user_id, "email": user.email, "role": user.role}}), 201

    @auth_bp.post("/login")
    def login():
        payload = request.get_json(silent=True) or {}
        try:
            user, token = service.login(payload.get("email"), payload.get("password"))
        except (ValidationError, InvalidCredentialsError):
            return jsonify({"error": {"code": "invalid_credentials"}}), 401

        return jsonify({"token": token, "user": {"id": user.user_id, "email": user.email, "role": user.role}}), 200

    @auth_bp.get("/me")
    def me():
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer", "", 1).strip() if auth_header else ""
        try:
            user = service.me(token)
        except InvalidCredentialsError:
            return jsonify({"error": {"code": "invalid_credentials"}}), 401

        return jsonify({"user": {"id": user.user_id, "email": user.email, "role": user.role}}), 200

    @auth_bp.post("/logout")
    def logout():
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer", "", 1).strip() if auth_header else ""
        try:
            service.logout(token)
        except InvalidCredentialsError:
            return jsonify({"error": {"code": "invalid_credentials"}}), 401

        return jsonify({"token_revoked": True}), 200

    return service, auth_bp


__all__ = [
    "AuthService",
    "AuthUser",
    "DuplicateIdentityError",
    "InMemoryUserStore",
    "InvalidCredentialsError",
    "PBKDF2PasswordHasher",
    "StatelessTokenManager",
    "ValidationError",
    "create_auth_blueprint",
    "create_standalone_auth",
]
