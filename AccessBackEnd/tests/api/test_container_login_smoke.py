from app.db import init_flask_database
from app.extensions import db
from app.models import User

import manage as backend_manage


def test_container_login_smoke(client, app):
    with app.app_context():
        init_flask_database(app)
        seeded = backend_manage.seed_all_from_sql(app.config["SQLALCHEMY_DATABASE_URI"])
        print(f"[container-login-smoke] seed_all_from_sql returned: {seeded}")

    if not seeded:
        register_payload = {
            "email": "admin.seed@example.com",
            "password": "Password123!",
            "role": "admin",
        }
        register_response = client.post("/api/v1/auth/register", json=register_payload)
        print(f"[container-login-smoke] register status={register_response.status_code}")
        print(f"[container-login-smoke] register payload={register_response.get_json()}")
        assert register_response.status_code in (201, 409)

    login_payload = {
        "email": "admin.seed@example.com",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    data = response.get_json()

    print(f"[container-login-smoke] login status={response.status_code}")
    print(f"[container-login-smoke] login payload={data}")

    assert response.status_code == 200
    assert data["user"]["email"] == "admin.seed@example.com"

    with app.app_context():
        user_count = db.session.query(User).count()
        print(f"[container-login-smoke] users_in_db={user_count}")
        assert user_count >= 1
