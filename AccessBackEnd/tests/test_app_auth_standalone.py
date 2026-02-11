from __future__ import annotations

from flask import Flask

from app.auth import create_standalone_auth


def _client():
    app = Flask(__name__)
    _, auth_bp = create_standalone_auth(url_prefix="/auth")
    app.register_blueprint(auth_bp)
    return app.test_client()


def test_register_login_me_logout_flow():
    client = _client()

    register_response = client.post(
        "/auth/register",
        json={"email": "Student@One.Example", "password": "pw-123", "role": "student"},
    )
    assert register_response.status_code == 201
    assert register_response.get_json()["user"]["email"] == "student@one.example"

    login_response = client.post(
        "/auth/login",
        json={"email": "student@one.example", "password": "pw-123"},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["email"] == "student@one.example"

    logout_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 200
    assert logout_response.get_json()["token_revoked"] is True

    post_logout_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert post_logout_me.status_code == 401


def test_register_and_login_validation_errors():
    client = _client()

    missing_payload = client.post("/auth/register", json={"email": ""})
    assert missing_payload.status_code == 400
    assert missing_payload.get_json()["error"]["code"] == "invalid_payload"

    client.post("/auth/register", json={"email": "user@example.com", "password": "pw"})

    duplicate = client.post("/auth/register", json={"email": "user@example.com", "password": "pw"})
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "email_exists"

    bad_login = client.post("/auth/login", json={"email": "user@example.com", "password": "wrong"})
    assert bad_login.status_code == 401
    assert bad_login.get_json()["error"]["code"] == "invalid_credentials"
