import sys
from pathlib import Path

import pytest

flask = pytest.importorskip("flask")
Flask = flask.Flask

APP_DIR = Path(__file__).resolve().parents[3] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from auth.auth_methods import AuthService, InMemoryUserStore, PBKDF2PasswordHasher, StatelessTokenManager  # noqa: E402
from auth.auth_routes import create_auth_blueprint  # noqa: E402


def build_client():
    app = Flask(__name__)
    service = AuthService(
        user_store=InMemoryUserStore(),
        password_hasher=PBKDF2PasswordHasher(),
        token_manager=StatelessTokenManager(secret_key="route-secret", ttl_seconds=300),
    )
    app.register_blueprint(create_auth_blueprint(service, url_prefix="/auth"))
    app.testing = True
    return app.test_client()


def test_register_and_login_endpoints_work_standalone():
    client = build_client()

    register = client.post("/auth/register", json={"identifier": "user@example.com", "password": "pw-12345"})
    assert register.status_code == 201

    login = client.post("/auth/login", json={"identifier": "user@example.com", "password": "pw-12345"})
    assert login.status_code == 200
    body = login.get_json()
    assert body["user"]["identifier"] == "user@example.com"
    assert "token" in body


def test_verify_endpoint_rejects_missing_or_invalid_token():
    client = build_client()

    response = client.get("/auth/verify")
    assert response.status_code == 401

    invalid = client.get("/auth/verify", headers={"Authorization": "Bearer bad-token"})
    assert invalid.status_code == 401
