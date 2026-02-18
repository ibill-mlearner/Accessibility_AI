from pathlib import Path

import pytest


def _authenticate_api_client(
    app,
    client,
    email: str = "apitester@example.com",
    role: str = "student",
) -> None:
    from app.db import init_flask_database
    from app.extensions import db

    init_flask_database(app)

    response = client.post(
        "/api/v1/api_view/register",
        json={"email": email, "password": "password123", "role": role},
    )
    assert response.status_code == 201


def _stub_ollama_provider(app, monkeypatch, *, result: str = "ok") -> None:
    """Patch AI provider invoke with deterministic Ollama-shaped payload."""

    app.config["AI_PROVIDER"] = "ollama"

    def _invoke(request):  # noqa: ANN001
        return {
            "result": result,
            "meta": {
                "provider": "ollama",
                "model_id": app.config.get("AI_OLLAMA_MODEL"),
                "endpoint": app.config.get("AI_OLLAMA_ENDPOINT"),
            },
        }

    ai_service = app.extensions["ai_service"]
    wrapped_service = getattr(ai_service, "_wrapped", ai_service)
    wrapped_service.config.provider = "ollama"
    monkeypatch.setattr(wrapped_service._provider, "invoke", _invoke)


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


def test_health_endpoint_is_public(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "ai_provider" in body


def test_health_endpoint(app, client):
    app.config["AI_PROVIDER"] = "ollama"

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["ai_provider"] == "ollama"


def test_resource_endpoints_return_user_chats(app, client):
    _authenticate_api_client(app, client)

    class_response = client.post(
        "/api/v1/classes",
        json={"name": "Bio 103", "description": "lecture recap context", "role": "student"},
    )
    assert class_response.status_code == 201
    class_id = class_response.get_json()["id"]

    created = client.post(
        "/api/v1/chats",
        json={"title": "Bio 103 lecture recap", "class_id": class_id, "model": "gpt-4o-mini"},
    )
    assert created.status_code == 201

    response = client.get("/api/v1/chats")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data and data[0]["title"] == "Bio 103 lecture recap"
    assert {"id", "title", "start", "model", "class", "user"}.issubset(data[0].keys())


def test_resource_create_returns_serialized_chat(app, client):
    _authenticate_api_client(app, client)

    class_response = client.post(
        "/api/v1/classes",
        json={"name": "Physics 100", "description": "chat create", "role": "student"},
    )
    class_id = class_response.get_json()["id"]

    response = client.post(
        "/api/v1/chats",
        json={"title": "Chat 99", "class_id": class_id, "model": "gpt-4o-mini"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["title"] == "Chat 99"
    assert payload["class_id"] == class_id


def test_resource_update_changes_chat_fields(app, client):
    _authenticate_api_client(app, client)

    class_response = client.post(
        "/api/v1/classes",
        json={"name": "Chem 101", "description": "chat update", "role": "student"},
    )
    class_id = class_response.get_json()["id"]
    create_response = client.post(
        "/api/v1/chats",
        json={"title": "Original", "class_id": class_id, "model": "gpt-4o-mini"},
    )
    chat_id = create_response.get_json()["id"]

    response = client.put(f"/api/v1/chats/{chat_id}", json={"title": "Renamed Chat"})
    assert response.status_code == 200
    assert response.get_json()["title"] == "Renamed Chat"


def test_resource_delete_returns_deleted_record(app, client):
    _authenticate_api_client(app, client)

    class_response = client.post(
        "/api/v1/classes",
        json={"name": "Calc 1", "description": "chat delete", "role": "student"},
    )
    class_id = class_response.get_json()["id"]
    create_response = client.post(
        "/api/v1/chats",
        json={"title": "Delete Me", "class_id": class_id, "model": "gpt-4o-mini"},
    )
    chat_id = create_response.get_json()["id"]

    response = client.delete(f"/api/v1/chats/{chat_id}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == chat_id


def test_ai_interaction_requires_authentication(client):
    response = client.post("/api/v1/ai/interactions", json={"prompt": "hello"})
    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "authentication required"


def test_ai_interaction_accepts_future_growth_fields(app, client, monkeypatch):
    _stub_ollama_provider(app, monkeypatch, result="hello")
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
    assert body["meta"]["provider"] == "ollama"
    assert body["meta"]["model_id"] == app.config["AI_OLLAMA_MODEL"]
    assert body["meta"]["endpoint"] == app.config["AI_OLLAMA_ENDPOINT"]
    assert body["meta"]["pipeline"] == "app.services.ai_pipeline"
    assert body["meta"]["selected_provider"] == "ollama"


def test_ai_interaction_succeeds_with_unwrapped_pipeline_service(app, client, monkeypatch):
    _stub_ollama_provider(app, monkeypatch, result="unwrapped")
    _authenticate_api_client(app, client)

    ai_service = app.extensions["ai_service"]
    app.extensions["ai_service"] = getattr(ai_service, "_wrapped", ai_service)

    from app.db import init_flask_database

    init_flask_database(app)

    response = client.post(
        "/api/v1/ai/interactions",
        json={"prompt": "works without logger", "context": {"class_id": 1}},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "unwrapped"


def test_ai_interaction_persists_record(app, client, monkeypatch):
    _stub_ollama_provider(app, monkeypatch, result="persisted")
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
        assert interactions[0].provider == "ollama"
        assert interactions[0].response_text


def test_ai_interaction_returns_structured_error_when_persistence_fails(app, client, monkeypatch):
    _stub_ollama_provider(app, monkeypatch, result="hello")
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


def test_ai_interaction_value_error_includes_structured_details(app, client, monkeypatch):
    _authenticate_api_client(app, client)

    from app.db import init_flask_database

    init_flask_database(app)

    ai_service = app.extensions["ai_service"]
    wrapped_service = getattr(ai_service, "_wrapped", ai_service)

    def _raise_value_error(*, prompt, context, initiated_by):  # noqa: ANN001
        raise ValueError("Extra data: line 2 column 1 (char 85)")

    monkeypatch.setattr(wrapped_service, "run_interaction", _raise_value_error)

    payload = {
        "prompt": "asdfasdf",
        "chat_id": 1,
        "context": {
            "chat_id": 1,
            "class_id": 1,
            "messages": [{"role": "user", "content": "asdfasdf"}],
        },
    }

    response = client.post("/api/v1/ai/interactions", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"] == "Extra data: line 2 column 1 (char 85)"
    assert body["error"]["details"] == {"exception": "ValueError", "source": "hf_output_parse"}


def test_unmatched_route_returns_json_error(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.get_json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"


def test_messages_resource_has_chat_relationship(app, client):
    _authenticate_api_client(app, client)

    class_response = client.post(
        "/api/v1/classes",
        json={"name": "Bio 110", "description": "messages", "role": "student"},
    )
    class_id = class_response.get_json()["id"]
    chat_response = client.post(
        "/api/v1/chats",
        json={"title": "Message chat", "class_id": class_id, "model": "gpt-4o-mini"},
    )
    chat_id = chat_response.get_json()["id"]

    create_message = client.post(
        "/api/v1/messages",
        json={"chat_id": chat_id, "message_text": "What is ATP?", "help_intent": "summarization"},
    )
    assert create_message.status_code == 201

    response = client.get("/api/v1/messages")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data and data[0]["chat_id"] == chat_id
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

    feature_create = client.post(
        "/api/v1/features",
        json={
            "title": "Outline mode",
            "description": "Concise bulleted responses",
            "enabled": True,
            "instructor_id": 1,
            "class_id": 1,
        },
    )
    assert feature_create.status_code == 201

    response = client.get("/api/v1/features")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data and data[0]["instructor_id"] == 1
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
    assert service.config.model_name == app.config["AI_MODEL_NAME"]
    assert service.config.ollama_model_id == "llama3.2:3b"
    assert service.config.ollama_options == {"temperature": 0.05}


def test_classes_resource_returns_instructor_and_section_metadata(app, client):
    _authenticate_api_client(app, client, email="instructor.meta@example.com", role="instructor")

    response = client.post(
        "/api/v1/classes",
        json={
            "name": "Biology 102",
            "role": "student",
            "description": "Spring section",
            "instructor_id": 1,
            "term": "2026-SPRING",
            "section_code": "B02",
            "external_class_key": "BIO-102-2026-SPRING-B02",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["instructor_id"] == 1
    assert payload["section"]["term"] == "2026-SPRING"
    assert payload["section"]["section_code"] == "B02"
    assert payload["instructor"]["id"] == 1


def test_chat_read_requires_membership_or_ownership(app, client):
    _authenticate_api_client(app, client, email="instructor.chat@example.com", role="instructor")

    class_response = client.post(
        "/api/v1/classes",
        json={
            "name": "Physics 201",
            "role": "student",
            "description": "Class for membership checks",
            "instructor_id": 1,
            "term": "2026-FALL",
            "section_code": "P01",
            "external_class_key": "PHY-201-2026-FALL-P01",
        },
    )
    class_id = class_response.get_json()["id"]

    chat_response = client.post(
        "/api/v1/chats",
        json={
            "title": "Kinematics prep",
            "start": "2026-09-01T00:00:00+00:00",
            "model": "gpt-4o-mini",
            "class": class_id,
            "user": 1,
        },
    )
    assert chat_response.status_code == 201
    chat_id = chat_response.get_json()["id"]

    outsider_client = app.test_client()
    _authenticate_api_client(app, outsider_client, email="outsider@example.com", role="student")

    unauthorized = outsider_client.get(f"/api/v1/chats/{chat_id}")
    assert unauthorized.status_code == 403
    assert unauthorized.get_json()["error"]["message"] == "user is not authorized for this chat"
