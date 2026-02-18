from __future__ import annotations


def _authenticate(app, client, *, email: str = "tester@example.com", role: str = "student") -> None:
    from app.db import init_flask_database

    init_flask_database(app)
    response = client.post(
        "/api/v1/api_view/register",
        json={"email": email, "password": "password123", "role": role},
    )
    assert response.status_code == 201


def _create_class_and_chat(client):
    class_response = client.post(
        "/api/v1/classes",
        json={
            "name": "Biology 101",
            "description": "Foundations",
        },
    )
    assert class_response.status_code == 201
    class_id = class_response.get_json()["id"]

    chat_response = client.post(
        "/api/v1/chats",
        json={
            "title": "Lecture recap",
            "class_id": class_id,
            "model": "gpt-4o-mini",
        },
    )
    assert chat_response.status_code == 201
    chat_id = chat_response.get_json()["id"]
    return class_id, chat_id


def test_chat_collection_endpoint_returns_list_shape(app, client):
    _authenticate(app, client)
    _create_class_and_chat(client)

    list_response = client.get("/api/v1/chats")
    assert list_response.status_code == 200
    payload = list_response.get_json()

    assert isinstance(payload, list)
    assert payload
    assert {"id", "title", "start", "model", "class", "user"}.issubset(payload[0].keys())

def test_chat_item_endpoints_round_trip(app, client):
    _authenticate(app, client)
    _class_id, chat_id = _create_class_and_chat(client)

    get_response = client.get(f"/api/v1/chats/{chat_id}")
    assert get_response.status_code == 200

    patch_response = client.patch(f"/api/v1/chats/{chat_id}", json={"title": "Updated"})
    assert patch_response.status_code == 200
    assert patch_response.get_json()["title"] == "Updated"

    delete_response = client.delete(f"/api/v1/chats/{chat_id}")
    assert delete_response.status_code == 200


def test_classes_features_messages_notes_endpoints_round_trip(app, client):
    _authenticate(app, client)
    class_id, chat_id = _create_class_and_chat(client)

    class_get = client.get(f"/api/v1/classes/{class_id}")
    assert class_get.status_code == 200
    assert class_get.get_json()["name"] == "Biology 101"

    feature_create = client.post(
        "/api/v1/features",
        json={
            "title": "Outline mode",
            "description": "Concise bullets",
            "enabled": True,
            "instructor_id": 1,
            "class_id": class_id,
        },
    )
    assert feature_create.status_code == 201
    feature_id = feature_create.get_json()["id"]

    feature_get = client.get(f"/api/v1/features/{feature_id}")
    assert feature_get.status_code == 200

    message_create = client.post(
        "/api/v1/messages",
        json={
            "chat_id": chat_id,
            "message_text": "What is ATP?",
            "help_intent": "summarization",
        },
    )
    assert message_create.status_code == 201
    message_id = message_create.get_json()["id"]

    messages_list = client.get("/api/v1/messages")
    assert messages_list.status_code == 200
    assert any(item["id"] == message_id for item in messages_list.get_json())

    note_create = client.post(
        "/api/v1/notes",
        json={
            "class_id": class_id,
            "chat_id": chat_id,
            "noted_on": "2026-02-10",
            "content": "Cell respiration summary",
        },
    )
    assert note_create.status_code == 201
    note_id = note_create.get_json()["id"]

    note_get = client.get(f"/api/v1/notes/{note_id}")
    assert note_get.status_code == 200
    assert note_get.get_json()["content"] == "Cell respiration summary"
