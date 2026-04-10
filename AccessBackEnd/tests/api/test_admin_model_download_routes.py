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
        app.extensions["ai_service"].download_model = lambda model_id: {
            "provider": "huggingface",
            "model_id": model_id,
            "status": "downloaded",
        }

    _register(client, 'admin-model-download@example.com', role='admin')

    response = client.post('/api/v1/admin/model-downloads', json={"model_id": "Qwen/Qwen2.5-0.5B-Instruct"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "ok": True,
        "message": "Model download attempted.",
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "status": "downloaded",
        "download": {
            "provider": "huggingface",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
            "status": "downloaded",
        },
    }


def test_admin_model_download_route_rejects_non_admin_user(app, client):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)
        app.extensions["ai_service"].download_model = lambda model_id: {
            "provider": "huggingface",
            "model_id": model_id,
            "status": "downloaded",
        }

    _register(client, 'student-model-download@example.com', role='student')

    response = client.post('/api/v1/admin/model-downloads', json={"model_id": "Qwen/Qwen2.5-0.5B-Instruct"})
    assert response.status_code == 403


def test_admin_model_download_route_requires_model_id_via_marshmallow_validation(app, client):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)
        app.extensions["ai_service"].download_model = lambda model_id: {
            "provider": "huggingface",
            "model_id": model_id,
            "status": "downloaded",
        }

    _register(client, 'admin-missing-model-id@example.com', role='admin')

    response = client.post('/api/v1/admin/model-downloads', json={})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "invalid model_id payload; Marshmallow validation failed"
    assert payload["details"] == {"fields": {"model_id": ["Missing data for required field."]}}


def test_admin_model_download_route_returns_500_when_ai_service_missing(app, client):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)
        app.extensions.pop("ai_service", None)

    _register(client, "admin-no-ai-service@example.com", role="admin")

    response = client.post('/api/v1/admin/model-downloads', json={"model_id": "Qwen/Qwen2.5-0.5B-Instruct"})
    assert response.status_code == 500
    payload = response.get_json()
    assert payload == {
        "error": "ai_service not configured for model downloads",
        "details": {},
    }


def test_admin_model_download_route_returns_502_when_download_raises(app, client, caplog):
    from app.db import init_flask_database

    with app.app_context():
        init_flask_database(app)

        def _boom(_: str):
            raise RuntimeError("network timeout")

        app.extensions["ai_service"].download_model = _boom

    _register(client, "admin-download-error@example.com", role="admin")

    response = client.post('/api/v1/admin/model-downloads', json={"model_id": "Qwen/Qwen2.5-0.5B-Instruct"})
    assert response.status_code == 502
    payload = response.get_json()
    assert payload == {
        "error": "model download failed",
        "details": {"model_id": "Qwen/Qwen2.5-0.5B-Instruct"},
    }
    assert "admin model download failed for model_id=Qwen/Qwen2.5-0.5B-Instruct" in caplog.text
