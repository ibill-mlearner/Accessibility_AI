from __future__ import annotations


def test_api_v1_login_returns_user_role(app, client):
    from app.db import init_flask_database

    init_flask_database(app)

    register = client.post(
        '/api/v1/auth/register',
        json={'email': 'rolecheck@example.com', 'password': 'password123', 'role': 'student'},
    )
    assert register.status_code == 201

    login = client.post(
        '/api/v1/auth/login',
        json={'email': 'rolecheck@example.com', 'password': 'password123'},
    )
    assert login.status_code == 200

    body = login.get_json()
    assert body['user']['email'] == 'rolecheck@example.com'
    assert body['user']['role'] == 'student'
