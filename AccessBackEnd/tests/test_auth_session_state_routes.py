from datetime import UTC, datetime, timedelta

from ..app.db import init_flask_database
from ..app.extensions import db
from ..app.models import User, UserSession


def _register(client, *, email: str, password: str = "Password123!", role: str = "student"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert response.status_code == 201
    return response


def _get_current_auth_session_id(client) -> int:
    with client.session_transaction() as flask_session:
        return int(flask_session["auth_session_id"])


def test_auth_session_missing_session_id_returns_401(app, client):
    with app.app_context():
        init_flask_database(app)

    _register(client, email="missing-session@example.com")

    with client.session_transaction() as flask_session:
        flask_session.pop("auth_session_id", None)

    response = client.get("/api/v1/auth/session")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload["error"]["message"] == "session not found"
    assert payload["error"]["details"]["reason"] == "missing session ID"


def test_auth_session_expired_session_returns_401_and_revokes_record(app, client):
    with app.app_context():
        init_flask_database(app)

    _register(client, email="expired-session@example.com")
    auth_session_id = _get_current_auth_session_id(client)

    with app.app_context():
        session_record = db.session.get(UserSession, auth_session_id)
        session_record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session_record.revoked_at = datetime.max.replace(tzinfo=UTC)
        db.session.commit()

    response = client.get("/api/v1/auth/session")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload["error"]["message"] == "session expired"
    assert payload["error"]["details"]["reason"] == "expired"

    with app.app_context():
        session_record = db.session.get(UserSession, auth_session_id)
        assert session_record.revoked_at != datetime.max.replace(tzinfo=UTC)


def test_auth_session_revoked_session_returns_401(app, client):
    with app.app_context():
        init_flask_database(app)

    _register(client, email="revoked-session@example.com")
    auth_session_id = _get_current_auth_session_id(client)

    with app.app_context():
        session_record = db.session.get(UserSession, auth_session_id)
        session_record.revoked_at = datetime.now(UTC) - timedelta(seconds=1)
        db.session.commit()

    response = client.get("/api/v1/auth/session")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload["error"]["message"] == "session revoked"
    assert payload["error"]["details"]["reason"] == "revoked"


def test_auth_session_mismatched_session_returns_401(app, client):
    with app.app_context():
        init_flask_database(app)

    _register(client, email="primary-user@example.com")

    with app.app_context():
        second_user = User(email="secondary-user@example.com", role="student")
        second_user.set_password("Password123!")
        db.session.add(second_user)
        db.session.flush()

        mismatch_session = UserSession(
            user_id=int(second_user.id),
            token_hash="secondary-session-token",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            last_seen_at=datetime.now(UTC),
            revoked_at=datetime.max.replace(tzinfo=UTC),
        )
        db.session.add(mismatch_session)
        db.session.commit()
        mismatch_session_id = int(mismatch_session.id)

    with client.session_transaction() as flask_session:
        flask_session["auth_session_id"] = mismatch_session_id

    response = client.get("/api/v1/auth/session")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload["error"]["message"] == "session user mismatch"
    assert payload["error"]["details"]["reason"] == "session user mismatch"