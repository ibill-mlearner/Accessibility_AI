from __future__ import annotations

import base64
import hashlib
from flask_bcrypt import Bcrypt
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


@dataclass(frozen=True)
class AuthUser:
    """Minimal user shape for auth flows.

    This model is intentionally storage-agnostic so app/auth can be reused in
    other projects without pulling in ORM models.
    """

    user_id: str
    identifier: str
    password_hash: str
    created_at: datetime


class AuthError(Exception):
    """Base auth exception."""


class InvalidCredentialsError(AuthError):
    """Raised when credentials fail validation."""


class DuplicateIdentityError(AuthError):
    """Raised when trying to register an existing identity."""


class ValidationError(AuthError):
    """Raised when request data is incomplete or malformed."""


class UserStore(Protocol):
    """Persistence adapter contract for auth module."""

    def get_by_identifier(self, identifier: str) -> AuthUser | None:
        ...

    def create_user(self, identifier: str, password_hash: str) -> AuthUser:
        ...


class PasswordHasher(Protocol):
    """Hasher adapter contract for auth module."""

    def hash_password(self, password: str) -> str:
        ...

    def verify_password(self, password: str, encoded_hash: str) -> bool:
        ...

    def better_hash(self, password: str) -> str:
        ...

    def better_verify(self, password: str, encoded_hash: str) -> bool:
        ...

class PBKDF2PasswordHasher:
    """Framework-independent password hasher using stdlib primitives."""

    algorithm = "sha256"
    algorithm_two = "bcrypt"

    def __init__(self, iterations: int = 310_000, salt_length: int = 16) -> None:
        self.iterations = iterations
        self.salt_length = salt_length
        self.bcrypt = Bcrypt()

    def better_hash(self, password: str) -> str:
        if not password:
            raise ValidationError("password is required")
        return self.bcrypt.generate_password_hash(password).decode("utf-8")

    def hash_password(self, password: str) -> str:
        # if salt is None:
        #     salt = secrets.token_hex(16)
        # assert salt and isinstance(salt, str) and "$" not in salt
        # assert isinstance(password, str)
        # pw_hash = hashlib.pbkdf2_hmac(
        #     "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
        # )
        # b64_hash = base64.b64encode(pw_hash).decode("ascii").strip()
        # return "{}${}${}${}".format(ALGORITHM, iterations, salt, b64_hash)

        if not password:
            raise ValidationError("password is required")

        salt = secrets.token_bytes(self.salt_length)
        digest = hashlib.pbkdf2_hmac(
            self.algorithm,
            password.encode("utf-8"),
            salt,
            self.iterations,
        )
        return "$".join(
            [
                "pbkdf2",
                self.algorithm,
                str(self.iterations),
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(digest).decode("ascii"),
            ]
        )

    def better_verify(self, password: str, encoded_hash: str)-> bool:
        return self.bcrypt.check_password_hash(encoded_hash, password)

    def verify_password(self, password: str, encoded_hash: str) -> bool:
        # if (password_hash or "").count("$") != 3:
        #     return False
        # algorithm, iterations, salt, b64_hash = password_hash.split("$", 3)
        # iterations = int(iterations)
        # assert algorithm == ALGORITHM
        # compare_hash = hash_password(password, salt, iterations)
        # return secrets.compare_digest(password_hash, compare_hash)

        try:
            _prefix, algorithm, iterations, salt_b64, digest_b64 = encoded_hash.split("$", maxsplit=4)
            salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
            expected_digest = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
            computed_digest = hashlib.pbkdf2_hmac(
                algorithm,
                password.encode("utf-8"),
                salt,
                int(iterations),
            )
        except (ValueError, TypeError):
            return False

        return hmac.compare_digest(expected_digest, computed_digest)

#This is not a good way to handle JWTokens
# need to move this over to Flask-JWT-Extended
# JWTManager will handle token and user_loader cleaner, less code, less coupling
class StatelessTokenManager:
    """Small signed token manager that is independent from Flask/JWT libs."""

    def __init__(self, secret_key: str, ttl_seconds: int = 3600) -> None:
        if not secret_key:
            raise ValidationError("secret_key is required")
        self.secret_key = secret_key.encode("utf-8")
        self.ttl_seconds = ttl_seconds

    def issue_token(self, user: AuthUser) -> str:
        payload = {
            "sub": user.user_id,
            "identifier": user.identifier,
            "exp": int((datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)).timestamp()),
            "nonce": base64.urlsafe_b64encode(os.urandom(8)).decode("ascii"),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_part = base64.urlsafe_b64encode(payload_bytes).decode("ascii")
        signature = hmac.new(self.secret_key, payload_part.encode("ascii"), hashlib.sha256).digest()
        signature_part = base64.urlsafe_b64encode(signature).decode("ascii")
        return f"{payload_part}.{signature_part}"

    def verify_token(self, token: str) -> dict[str, str | int]:
        if not token or "." not in token:
            raise InvalidCredentialsError("token is invalid")

        payload_part, signature_part = token.split(".", maxsplit=1)
        expected_sig = hmac.new(self.secret_key, payload_part.encode("ascii"), hashlib.sha256).digest()

        try:
            provided_sig = base64.urlsafe_b64decode(signature_part.encode("ascii"))
            payload = json.loads(base64.urlsafe_b64decode(payload_part.encode("ascii")).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            raise InvalidCredentialsError("token is invalid") from None

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise InvalidCredentialsError("token signature mismatch")

        if int(payload.get("exp", 0)) <= int(datetime.now(UTC).timestamp()):
            raise InvalidCredentialsError("token expired")

        return payload


class InMemoryUserStore:
    """Reference store implementation for local tests and standalone usage."""

    def __init__(self) -> None:
        self._users: dict[str, AuthUser] = {}

    def get_by_identifier(self, identifier: str) -> AuthUser | None:
        return self._users.get(identifier)

    def create_user(self, identifier: str, password_hash: str) -> AuthUser:
        if identifier in self._users:
            raise DuplicateIdentityError("identity already exists")

        user = AuthUser(
            user_id=str(len(self._users) + 1),
            identifier=identifier,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )
        self._users[identifier] = user
        return user


class AuthService:
    """Core auth orchestration with no framework or ORM dependency."""

    def __init__(
        self,
        user_store: UserStore,
        password_hasher: PasswordHasher,
        token_manager: StatelessTokenManager,
    ) -> None:
        self.user_store = user_store
        self.password_hasher = password_hasher
        self.token_manager = token_manager

    # needed to add registration to project to make adding users easier
    def register(self, identifier: str, password: str) -> AuthUser:
        normalized_identifier = self._normalize_identifier(identifier)
        if self.user_store.get_by_identifier(normalized_identifier):
            raise DuplicateIdentityError("identity already exists")

        password_hash = self.password_hasher.hash_password(password)
        return self.user_store.create_user(normalized_identifier, password_hash)

    def login(self, identifier: str, password: str) -> tuple[AuthUser, str]:
        normalized_identifier = self._normalize_identifier(identifier)
        user = self.user_store.get_by_identifier(normalized_identifier)
        if user is None:
            raise InvalidCredentialsError("invalid credentials")

        if not self.password_hasher.verify_password(password, user.password_hash):
            raise InvalidCredentialsError("invalid credentials")

        return user, self.token_manager.issue_token(user)

    def verify_access_token(self, token: str) -> dict[str, str | int]:
        return self.token_manager.verify_token(token)

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        normalized = (identifier or "").strip().lower()
        if not normalized:
            raise ValidationError("identifier is required")
        return normalized
