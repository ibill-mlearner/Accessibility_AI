import os

os.environ.setdefault("TEST_AI_PROVIDER", "ollama")


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
    assert payload["selected"]["source"] in {"config_default", "db_first_available"}


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
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "source": "session_selection",
    }
