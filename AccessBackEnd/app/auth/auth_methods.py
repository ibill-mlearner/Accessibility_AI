from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe
from typing import Protocol


@dataclass(frozen=True)
class AuthUser:
    """Serializable auth user representation independent from ORM models."""

    id: int
    email: str
    role: str = "student"


class AuthError(ValueError):
    """Domain-level auth error with API-friendly metadata."""

    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class PasswordHasher(Protocol):
    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password: str, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, user: AuthUser) -> str: ...


class UserStore(Protocol):
    def get_by_email(self, email: str) -> dict | None: ...

    def create_user(self, email: str, password_hash: str, role: str = "student") -> AuthUser: ...


class SHA256PasswordHasher:
    """Simple hashing strategy suitable for standalone demos/tests."""

    def hash_password(self, password: str) -> str:
        return sha256(password.encode("utf-8")).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self.hash_password(password) == password_hash


class StatelessTokenIssuer:
    """Opaque token generator with no infrastructure dependency."""

    def issue(self, user: AuthUser) -> str:
        return token_urlsafe(32)


class InMemoryUserStore:
    """In-memory store to keep auth portable and framework-agnostic."""

    def __init__(self) -> None:
        self._users_by_email: dict[str, dict] = {}
        self._id_sequence = 1

    def get_by_email(self, email: str) -> dict | None:
        return self._users_by_email.get(email)

    def create_user(self, email: str, password_hash: str, role: str = "student") -> AuthUser:
        if email in self._users_by_email:
            raise AuthError("email already registered", code="email_exists", status_code=409)

        user = AuthUser(id=self._id_sequence, email=email, role=role)
        self._id_sequence += 1
        self._users_by_email[email] = {"user": user, "password_hash": password_hash}
        return user


class AuthService:
    """Standalone auth service with injectable persistence and token strategies."""

    def __init__(self, *, user_store: UserStore, password_hasher: PasswordHasher, token_issuer: TokenIssuer) -> None:
        self._user_store = user_store
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer
        self._active_tokens: dict[str, AuthUser] = {}

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    def register(self, *, email: str, password: str, role: str = "student") -> AuthUser:
        normalized_email = self._normalize_email(email)
        if not normalized_email or not password:
            raise AuthError("email and password are required", code="invalid_payload", status_code=400)

        password_hash = self._password_hasher.hash_password(password)
        return self._user_store.create_user(normalized_email, password_hash, role)

    def authenticate(self, *, email: str, password: str) -> AuthUser:
        normalized_email = self._normalize_email(email)
        record = self._user_store.get_by_email(normalized_email)
        if not record:
            raise AuthError("invalid credentials", code="invalid_credentials", status_code=401)

        if not self._password_hasher.verify_password(password, record["password_hash"]):
            raise AuthError("invalid credentials", code="invalid_credentials", status_code=401)

        return record["user"]

    def login(self, *, email: str, password: str) -> tuple[AuthUser, str]:
        user = self.authenticate(email=email, password=password)
        token = self._token_issuer.issue(user)
        self._active_tokens[token] = user
        return user, token

    def logout(self, token: str | None) -> bool:
        if not token:
            return False
        return self._active_tokens.pop(token, None) is not None

    def validate_token(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        return self._active_tokens.get(token)
