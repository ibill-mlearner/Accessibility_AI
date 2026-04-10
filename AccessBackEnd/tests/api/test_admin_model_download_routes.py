def _register(client, email: str, *, role: str):
    response = client.post(
        '/api/v1/auth/register',
        json={"email": email, "password": "Password123!", "role": role},
    )
    assert response.status_code == 201


def test_admin_model_download_route_returns_stub_json_for_admin(app, client):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)

    _register(client, 'admin-model-download@example.com', role='admin')

    response = client.post('/api/v1/admin/model-downloads', json={"model_id": "Qwen/Qwen2.5-0.5B-Instruct"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "ok": True,
        "message": "Hey, you reached me.",
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "status": "queued_stub",
    }


def test_admin_model_download_route_rejects_non_admin_user(app, client):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)

    _register(client, 'student-model-download@example.com', role='student')

    response = client.post('/api/v1/admin/model-downloads', json={"model_id": "Qwen/Qwen2.5-0.5B-Instruct"})
    assert response.status_code == 403


def test_admin_model_download_route_requires_model_id_via_marshmallow_validation(app, client):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)

    _register(client, 'admin-missing-model-id@example.com', role='admin')

    response = client.post('/api/v1/admin/model-downloads', json={})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "invalid model_id payload; Marshmallow validation failed"
    assert payload["details"] == {"fields": {"model_id": ["Missing data for required field."]}}
