import os
os.environ.setdefault("TEST_AI_PROVIDER", "ollama")

from app.db import init_flask_database
from app.extensions import db
from app.models import Accommodation, UserAccessibilityFeature


def _register(client, *, email: str, password: str = "Password123!", role: str = "student"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert response.status_code == 201


def test_feature_preferences_routes_read_and_update_current_user_preferences(app, client):
    with app.app_context():
        init_flask_database(app)
        db.session.add_all([
            Accommodation(title="Simplified language", details="A", active=True),
            Accommodation(title="Read-aloud cues", details="B", active=True),
            Accommodation(title="Font size 18px", details="standard; Use larger text.", active=True, font_size_px=18),
        ])
        db.session.commit()

    _register(client, email="feature-prefs@example.com")

    list_response = client.get('/api/v1/features/preferences')
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert len(list_payload) == 2
    assert all(item["enabled"] is False for item in list_payload)

    target_feature_id = int(list_payload[0]["accommodation_id"])
    update_response = client.patch(f'/api/v1/features/preferences/{target_feature_id}', json={"enabled": True})
    assert update_response.status_code == 200
    assert update_response.get_json()["enabled"] is True

    features_response = client.get('/api/v1/features')
    assert features_response.status_code == 200
    features_payload = features_response.get_json()
    assert all(not str(item.get("details", "")).lower().startswith("standard;") for item in features_payload)
    assert all(item["displayable"] is True for item in features_payload)
    enabled_map = {int(item["id"]): bool(item["enabled"]) for item in features_payload}
    assert enabled_map[target_feature_id] is True


def test_feature_create_supports_non_displayable_records(app, client):
    with app.app_context():
        init_flask_database(app)

    _register(client, email="feature-create@example.com")
    response = client.post(
        "/api/v1/features",
        json={
            "title": "Color profile: Deuteranopia-safe palette",
            "details": "RGB(0, 114, 178) RGB(230, 159, 0)",
            "active": True,
            "displayable": False,
            "color_family": "deuteranopia-safe",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["displayable"] is False
    assert payload["color_family"] == "deuteranopia-safe"


def test_feature_create_supports_font_family_metadata(app, client):
    with app.app_context():
        init_flask_database(app)

    _register(client, email="feature-font-family@example.com")
    response = client.post(
        "/api/v1/features",
        json={
            "title": "Font family: Sans-serif",
            "details": "Prefer sans-serif fonts.",
            "active": True,
            "displayable": True,
            "font_family": "sans-serif",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["font_family"] == "sans-serif"


def test_feature_preferences_replace_endpoint_upserts_records(app, client):
    with app.app_context():
        init_flask_database(app)
        db.session.add_all([
            Accommodation(title="Bullet-point summaries", details="A", active=True),
            Accommodation(title="Extra spacing", details="B", active=True),
        ])
        db.session.commit()

    _register(client, email="feature-prefs-replace@example.com")

    features = client.get('/api/v1/features').get_json()
    payload = {
        "preferences": [
            {"accommodation_id": int(features[0]["id"]), "enabled": True},
            {"accommodation_id": int(features[1]["id"]), "enabled": False},
        ]
    }
    response = client.put('/api/v1/features/preferences', json=payload)
    assert response.status_code == 200

    with app.app_context():
        rows = db.session.query(UserAccessibilityFeature).all()
        assert len(rows) == 2
        enabled_by_feature = {int(row.accommodation_id): bool(row.enabled) for row in rows}
        assert enabled_by_feature[int(features[0]["id"])] is True
        assert enabled_by_feature[int(features[1]["id"])] is False
