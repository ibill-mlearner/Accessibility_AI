import os

os.environ["TEST_AI_PROVIDER"] = "ollama"
os.environ["AI_PROVIDER"] = "ollama"


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "student"},
    )
    assert response.status_code == 201


def test_ai_catalog_reads_models_from_db_and_ignores_invalid_session_selection(app, client):
    from app.api.v1 import ai_model_catalog_routes as catalog_routes

    catalog_routes._ai_catalog_cache.clear()
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import AIModel

    with app.app_context():
        init_flask_database(app)

    _register(client, "catalog-db@example.com")

    with app.app_context():
        db.session.add(AIModel(provider="ollama", model_id="llama3.2:3b", source="seed", active=True))
        db.session.add(AIModel(provider="huggingface", model_id="Qwen/Qwen2.5-0.5B-Instruct", source="seed", active=True))
        db.session.commit()

    with client.session_transaction() as sess:
        sess["ai_model_selection"] = {
            "user_id": 999999,
            "provider": "huggingface",
            "model_id": "does-not-exist",
        }

    response = client.get("/api/v1/ai/catalog")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["models"]
    assert {model["provider"] for model in payload["models"]} == {"huggingface", "ollama"}
    assert payload["selected"]["source"] in {"config_default", "db_first_available", "catalog_fallback"}


def test_ai_catalog_prefers_valid_session_selection_from_db_models(app, client):
    from app.api.v1 import ai_model_catalog_routes as catalog_routes

    catalog_routes._ai_catalog_cache.clear()
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import AIModel, DBUser

    with app.app_context():
        init_flask_database(app)

    email = "catalog-session@example.com"
    _register(client, email)

    with app.app_context():
        user = db.session.query(DBUser).filter(DBUser.email == email).one()
        db.session.add(AIModel(provider="huggingface", model_id="Qwen/Qwen2.5-0.5B-Instruct", source="seed", active=True))
        db.session.commit()
        user_id = int(user.id)

    with client.session_transaction() as sess:
        sess["ai_model_selection"] = {
            "user_id": user_id,
            "auth_session_id": sess.get("auth_session_id"),
            "provider": "huggingface",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        }

    response = client.get("/api/v1/ai/catalog")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["selected"] == {
        "provider": "huggingface",
        "id": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "source": "session_selection",
    }


def test_ai_selection_accepts_model_id_from_models_available_payload(app, client):
    from app.db import init_flask_database

    class _InventoryService:
        def list_available_models(self):
            return {
                "huggingface_local": {
                    "models": [
                        {
                            "id": "/workspace/instance/models/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/123abc",
                        }
                    ],
                },
                "local": {
                    "models": [
                        {
                            "id": "/workspace/instance/models/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/123abc",
                        }
                    ],
                },
            }

    with app.app_context():
        init_flask_database(app)

    _register(client, "catalog-selection-available@example.com")
    app.extensions["ai_service"] = _InventoryService()

    available_response = client.get("/api/v1/ai/models/available")
    assert available_response.status_code == 200
    available_payload = available_response.get_json()
    model_id = available_payload["local"]["models"][0]["id"]

    selection_response = client.post(
        "/api/v1/ai/selection",
        json={"provider": "huggingface", "model_id": model_id},
    )
    assert selection_response.status_code == 200
    selection_payload = selection_response.get_json()
    assert selection_payload["provider"] == "huggingface"
    assert selection_payload["id"] == model_id
    assert selection_payload["model_id"] == model_id


def test_models_available_public_shape_hides_internal_envelopes(app, client):
    from app.db import init_flask_database

    class _InventoryService:
        def list_available_models(self):
            return {
                "model_defaults": {
                    "model_name": "Qwen/Qwen2.5-0.5B-Instruct",
                    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
                },
                "local": {
                    "models": [
                        {
                            "id": "Qwen/Qwen2.5-0.5B-Instruct",
                            "path": "/tmp/models/qwen",
                            "size": 123,
                            "source": "huggingface_local",
                        }
                    ],
                    "count": 1,
                },
                "meta": {
                    "warnings": [{"source": "inventory", "message": "sample warning"}],
                    "cache_hit": False,
                },
            }

    with app.app_context():
        init_flask_database(app)

    _register(client, "available-shape@example.com")
    app.extensions["ai_service"] = _InventoryService()

    response = client.get("/api/v1/ai/models/available")
    assert response.status_code == 200

    payload = response.get_json()
    assert "model_defaults" in payload
    assert "warnings" in payload
    assert "local" in payload
    assert "meta" not in payload
    assert "huggingface_local" not in payload

    models = payload["local"]["models"]
    assert models
    assert "id" in models[0]
    assert "path" not in models[0]
    assert "size" not in models[0]
    assert "source" not in models[0]
