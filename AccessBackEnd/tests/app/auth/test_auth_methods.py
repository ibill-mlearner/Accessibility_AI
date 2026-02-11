import sys
import time
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[3] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from auth.auth_methods import (  # noqa: E402
    AuthService,
    DuplicateIdentityError,
    InMemoryUserStore,
    InvalidCredentialsError,
    PBKDF2PasswordHasher,
    StatelessTokenManager,
)


def build_service(ttl_seconds: int = 300) -> AuthService:
    return AuthService(
        user_store=InMemoryUserStore(),
        password_hasher=PBKDF2PasswordHasher(),
        token_manager=StatelessTokenManager(secret_key="test-secret", ttl_seconds=ttl_seconds),
    )


def test_register_login_and_verify_token_round_trip():
    service = build_service()

    created = service.register("Student@School.edu", "strong-password")
    user, token = service.login("student@school.edu", "strong-password")
    claims = service.verify_access_token(token)

    assert created.identifier == "student@school.edu"
    assert user.user_id == created.user_id
    assert claims["identifier"] == "student@school.edu"
    assert claims["sub"] == created.user_id


def test_register_rejects_duplicate_identity():
    service = build_service()
    service.register("dup@example.com", "pass-1")

    with pytest.raises(DuplicateIdentityError):
        service.register("dup@example.com", "pass-2")


def test_login_rejects_wrong_password():
    service = build_service()
    service.register("student@example.com", "correct-pass")

    with pytest.raises(InvalidCredentialsError):
        service.login("student@example.com", "wrong-pass")


def test_verify_rejects_expired_tokens():
    service = build_service(ttl_seconds=1)
    service.register("expiring@example.com", "pass")
    _user, token = service.login("expiring@example.com", "pass")

    time.sleep(1.1)

    with pytest.raises(InvalidCredentialsError):
        service.verify_access_token(token)
