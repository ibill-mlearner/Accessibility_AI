from AccessBackEnd.app import create_app


def test_app_factory_registers_extensions_and_blueprints():
    app = create_app("testing")

    assert "api_v1" in app.blueprints
    assert "auth" in app.blueprints
    assert "event_bus" in app.extensions
    assert "ai_service" in app.extensions


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["ai_provider"] == "mock_json"
