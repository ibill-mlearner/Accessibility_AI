from pathlib import Path

import pytest


def _authenticate_api_client(app, client, email: str = "apitester@example.com") -> None:
    from app.db import init_flask_database
    from app.extensions import db

    init_flask_database(app)

    response = client.post(
        "/api/v1/api_view/register",
        json={"email": email, "password": "password123", "role": "student"},
    )
    assert response.status_code == 201


def test_app_factory_registers_extensions_and_blueprints():
    try:
        from app import create_app
    except ModuleNotFoundError as exc:
        pytest.skip(f"create_app import unavailable due to missing dependency: {exc}")

    app = create_app("testing")

    assert "api_v1" in app.blueprints
    assert "auth" in app.blueprints
    assert "event_bus" in app.extensions
    assert "ai_service" in app.extensions


def test_initialize_logging_is_idempotent():
    from app import create_app
    from app.services.logging import (
        InteractionLoggingService,
        LoggingObserver,
        initialize_logging,
    )

    app = create_app("testing")

    assert isinstance(app.extensions["ai_service"], InteractionLoggingService)
    event_bus = app.extensions["event_bus"]
    initial_observer_count = len(event_bus._observers)

    initialize_logging(app)

    assert isinstance(app.extensions["ai_service"], InteractionLoggingService)
    assert len(event_bus._observers) == initial_observer_count
    assert sum(
        isinstance(observer, LoggingObserver) for observer in event_bus._observers
    ) == 1


def test_health_endpoint_requires_authentication(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["code"] == "unauthorized"


def test_health_endpoint(app, client):
    _authenticate_api_client(app, client)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["ai_provider"] == "mock_json"


def test_resource_endpoints_return_seed_data(app, client):
    _authenticate_api_client(app, client)

    response = client.get("/api/v1/chats")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data and data[0]["title"] == "Bio 103 lecture recap"
    assert {"id", "title", "start", "model", "class", "user"}.issubset(data[0].keys())


def test_resource_create_is_passthrough(app, client):
    _authenticate_api_client(app, client)

    payload = {"id": 99, "title": "Chat 99", "meta": {"tag": "passthrough"}}
    response = client.post("/api/v1/chats", json=payload)
    assert response.status_code == 201
    assert response.get_json() == payload


def test_resource_update_replaces_record_without_transform(app, client):
    _authenticate_api_client(app, client)

    payload = {"id": 1, "title": "Renamed Chat", "extra": ["a", "b"]}
    response = client.put("/api/v1/chats/1", json=payload)
    assert response.status_code == 200
    assert response.get_json() == payload


def test_resource_delete_returns_deleted_record(app, client):
    _authenticate_api_client(app, client)

    response = client.delete("/api/v1/chats/2")
    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == 2


def test_ai_interaction_requires_authentication(client):
    response = client.post("/api/v1/ai/interactions", json={"prompt": "hello"})
    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "authentication required"


def test_ai_interaction_accepts_future_growth_fields(app, client):
    _authenticate_api_client(app, client)

    payload = {
        "prompt": "hello",
        "system_prompt": "You are a helpful note assistant",
        "rag": {"source": "vector_db", "query": "biology 103 chapter 1"},
        "context": {"class_id": 1},
    }

    from app.db import init_flask_database

    init_flask_database(app)

    response = client.post("/api/v1/ai/interactions", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert "meta" in body
    assert body["meta"]["prompt_echo"] == "hello"


def test_ai_interaction_persists_record(app, client):
    _authenticate_api_client(app, client)

    from app.db import init_flask_database
    from app.extensions import db
    from app.models import AIInteraction

    init_flask_database(app)

    payload = {
        "prompt": "persist this interaction",
        "context": {"class_id": 1},
    }
    response = client.post("/api/v1/ai/interactions", json=payload)

    assert response.status_code == 200

    with app.app_context():
        interactions = db.session.query(AIInteraction).all()
        assert len(interactions) == 1
        assert interactions[0].prompt == payload["prompt"]
        assert interactions[0].provider == "mock_json"
        assert interactions[0].response_text


def test_ai_interaction_returns_structured_error_when_persistence_fails(app, client, monkeypatch):
    _authenticate_api_client(app, client)

    from app.db import init_flask_database
    from app.extensions import db

    init_flask_database(app)

    from sqlalchemy.exc import SQLAlchemyError

    def _raise_sql_error() -> None:
        raise SQLAlchemyError("forced commit failure")

    monkeypatch.setattr(db.session, "commit", _raise_sql_error)

    response = client.post("/api/v1/ai/interactions", json={"prompt": "hello"})

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"]["code"] == "persistence_error"


def test_unmatched_route_returns_json_error(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.get_json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"


def test_messages_resource_has_chat_relationship(app, client):
    _authenticate_api_client(app, client)

    response = client.get("/api/v1/messages")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data and data[0]["chat_id"] == 1
    assert {"id", "chat_id", "message_text", "vote", "note", "help_intent"}.issubset(data[0].keys())


def test_resource_not_found_uses_json_error_envelope(app, client):
    _authenticate_api_client(app, client)

    response = client.get("/api/v1/classes/999")
    assert response.status_code == 404
    body = response.get_json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "class not found"
    assert body["error"]["details"]["id"] == 999


def test_create_resource_requires_json_object(app, client):
    _authenticate_api_client(app, client)

    response = client.post("/api/v1/chats", json=[{"id": 7}])
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"] == "json object body required"


def test_features_resource_includes_instructor_and_class_associations(app, client):
    _authenticate_api_client(app, client)

    response = client.get("/api/v1/features")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data and data[0]["instructor_id"] == 4
    assert data and data[0]["class_id"] == 1
    assert {"id", "title", "description", "enabled", "instructor_id", "class_id"}.issubset(data[0].keys())


def test_api_view_page_renders(client):
    response = client.get("/api/v1/api_view")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    body = response.get_data(as_text=True)
    assert "API v1 Test View" in body
    assert "/api/v1/health" in body
    assert "/api/v1/api_view/register" in body
    assert "/api/v1/api_view/login" in body
    assert "/api/v1/api_view/logout" in body


def test_api_view_register_creates_user_and_returns_session_token(app, client):
    from app.db import init_flask_database
    from app.extensions import db

    init_flask_database(app)

    response = client.post(
        "/api/v1/api_view/register",
        json={"email": "newstudent@example.com", "password": "password123", "role": "student"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["message"] == "registration successful"
    assert body["user"]["email"] == "newstudent@example.com"
    assert body["user"]["role"] == "student"
    assert isinstance(body["session_token"], str)
    assert body["session_token"]


def test_api_view_login_returns_session_token(app, client):
    from app.db import init_flask_database
    from app.extensions import db

    init_flask_database(app)

    register_response = client.post(
        "/auth/register",
        json={"email": "student@example.com", "password": "password123", "role": "student"},
    )
    assert register_response.status_code == 201

    response = client.post(
        "/api/v1/api_view/login",
        json={"email": "student@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "login successful"
    assert body["user"]["email"] == "student@example.com"
    assert isinstance(body["session_token"], str)
    assert body["session_token"]


def test_api_view_logout_clears_session(app, client):
    from app.db import init_flask_database

    init_flask_database(app)

    register_response = client.post(
        "/api/v1/api_view/register",
        json={"email": "logoutstudent@example.com", "password": "password123", "role": "student"},
    )
    assert register_response.status_code == 201

    response = client.post("/api/v1/api_view/logout")

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "logout successful"


def test_create_app_uses_backend_instance_directory():
    try:
        from app import create_app
        from app import config as app_config
    except ModuleNotFoundError as exc:
        pytest.skip(f"create_app import unavailable due to missing dependency: {exc}")

    app = create_app("testing")

    assert Path(app.instance_path) == app_config._INSTANCE_DIR


def test_init_db_cli_reports_resolved_database_uri(tmp_path):
    from app import create_app

    db_path = tmp_path / "cli-init.db"
    app = create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    runner = app.test_cli_runner()
    result = runner.invoke(args=["init-db"])

    assert result.exit_code == 0
    assert "Resolved SQLALCHEMY_DATABASE_URI:" in result.output
    assert db_path.as_posix() in result.output
    assert "Database schema initialized." in result.output


def test_build_ai_service_requires_ollama_endpoint_when_provider_is_ollama():
    from app import build_ai_service, create_app

    app = create_app("testing")
    app.config["AI_PROVIDER"] = "ollama"
    app.config["AI_OLLAMA_ENDPOINT"] = ""

    with pytest.raises(ValueError, match="AI_OLLAMA_ENDPOINT"):
        build_ai_service(app)


def test_build_ai_service_maps_explicit_ollama_config_fields():
    from app import build_ai_service, create_app

    app = create_app("testing")
    app.config.update(
        AI_PROVIDER="ollama",
        AI_OLLAMA_ENDPOINT="http://localhost:11434/api/chat",
        AI_OLLAMA_MODEL="llama3.2:3b",
        AI_OLLAMA_OPTIONS={"temperature": 0.05},
    )

    service = build_ai_service(app)

    assert service.config.ollama_endpoint == "http://localhost:11434/api/chat"
    assert service.config.ollama_model_id == "llama3.2:3b"
    assert service.config.ollama_options == {"temperature": 0.05}
