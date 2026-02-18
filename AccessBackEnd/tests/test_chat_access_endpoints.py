from datetime import datetime, timezone

from app.db import init_flask_database
from app.extensions import db
from app.models import AIInteraction, Chat, CourseClass, Message, UserClassEnrollment


def _register(client, email: str, role: str = "student") -> int:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "role": role},
    )
    assert response.status_code == 201
    return int(response.get_json()["user"]["id"])


def _seed_chat_context(app):
    init_flask_database(app)

    instructor_client = app.test_client()
    owner_client = app.test_client()
    peer_client = app.test_client()
    dropped_client = app.test_client()
    outsider_client = app.test_client()

    instructor_id = _register(instructor_client, "instructor.chat.access@example.com", "instructor")
    owner_id = _register(owner_client, "owner.chat.access@example.com", "student")
    peer_id = _register(peer_client, "peer.chat.access@example.com", "student")
    dropped_id = _register(dropped_client, "dropped.chat.access@example.com", "student")
    _register(outsider_client, "outsider.chat.access@example.com", "student")

    with app.app_context():
        class_record = CourseClass(
            role="student",
            name="Algebra II",
            description="Access control checks",
            instructor_id=instructor_id,
            term="2026-FALL",
            section_code="A02",
            external_class_key="ALG-2-2026-FALL-A02",
        )
        db.session.add(class_record)
        db.session.flush()

        db.session.add_all(
            [
                UserClassEnrollment(user_id=owner_id, class_id=class_record.id, role="student"),
                UserClassEnrollment(user_id=peer_id, class_id=class_record.id, role="student"),
                UserClassEnrollment(
                    user_id=dropped_id,
                    class_id=class_record.id,
                    role="student",
                    dropped_at=datetime.now(timezone.utc),
                ),
            ]
        )

        chat = Chat(title="Week 1 review", model="gpt-4o-mini", class_id=class_record.id, user_id=owner_id)
        db.session.add(chat)
        db.session.flush()

        db.session.add(
            Message(
                chat_id=chat.id,
                message_text="Explain factoring",
                vote="good",
                note="no",
                help_intent="homework",
            )
        )
        db.session.add(
            AIInteraction(
                chat_id=chat.id,
                prompt="Explain factoring",
                response_text="Factoring rewrites an expression as multiplied terms.",
                provider="mock_json",
            )
        )
        db.session.commit()

        class_id = class_record.id
        chat_id = chat.id

    return {
        "class_id": class_id,
        "chat_id": chat_id,
        "instructor_client": instructor_client,
        "owner_client": owner_client,
        "peer_client": peer_client,
        "dropped_client": dropped_client,
        "outsider_client": outsider_client,
        "owner_id": owner_id,
        "peer_id": peer_id,
        "dropped_id": dropped_id,
    }


def test_chat_message_access_for_owner_instructor_and_active_enrollment(app):
    context = _seed_chat_context(app)
    chat_id = context["chat_id"]

    owner_response = context["owner_client"].get(f"/api/v1/chats/{chat_id}/messages")
    instructor_response = context["instructor_client"].get(f"/api/v1/chats/{chat_id}/messages")
    peer_response = context["peer_client"].get(f"/api/v1/chats/{chat_id}/messages")

    assert owner_response.status_code == 200
    assert instructor_response.status_code == 200
    assert peer_response.status_code == 200


def test_chat_message_access_denies_dropped_or_non_enrolled_users(app):
    context = _seed_chat_context(app)
    chat_id = context["chat_id"]

    dropped_response = context["dropped_client"].get(f"/api/v1/chats/{chat_id}/messages")
    outsider_response = context["outsider_client"].post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"message_text": "Can I post?", "help_intent": "practice"},
    )

    assert dropped_response.status_code == 403
    assert dropped_response.get_json()["error"]["code"] == "forbidden"
    assert dropped_response.get_json()["error"]["message"] == "access denied"

    assert outsider_response.status_code == 403
    assert outsider_response.get_json()["error"]["code"] == "forbidden"
    assert outsider_response.get_json()["error"]["message"] == "access denied"


def test_chat_create_allows_instructor_or_active_enrollment_and_denies_otherwise(app):
    context = _seed_chat_context(app)

    owner_create = context["owner_client"].post(
        "/api/v1/chats",
        json={"class_id": context["class_id"], "title": "Owner chat"},
    )
    instructor_create_for_peer = context["instructor_client"].post(
        "/api/v1/chats",
        json={"class_id": context["class_id"], "user_id": context["peer_id"], "title": "Instructor made this"},
    )
    instructor_create_for_dropped = context["instructor_client"].post(
        "/api/v1/chats",
        json={"class_id": context["class_id"], "user_id": context["dropped_id"], "title": "Should fail"},
    )
    outsider_create = context["outsider_client"].post(
        "/api/v1/chats",
        json={"class_id": context["class_id"], "title": "Outsider chat"},
    )

    assert owner_create.status_code == 201
    assert owner_create.get_json()["user_id"] == context["owner_id"]

    assert instructor_create_for_peer.status_code == 201
    assert instructor_create_for_peer.get_json()["user_id"] == context["peer_id"]

    assert instructor_create_for_dropped.status_code == 403
    assert instructor_create_for_dropped.get_json()["error"]["message"] == "access denied"

    assert outsider_create.status_code == 403
    assert outsider_create.get_json()["error"]["message"] == "access denied"


def test_chat_create_backfills_default_class_for_legacy_payload_and_validates_user_id(app):
    context = _seed_chat_context(app)

    empty_class_response = context["owner_client"].post(
        "/api/v1/chats",
        json={"class": "", "title": "legacy payload"},
    )
    assert empty_class_response.status_code == 201
    assert empty_class_response.get_json()["class_id"] == context["class_id"]
    assert empty_class_response.get_json()["user_id"] == context["owner_id"]

    invalid_user_response = context["owner_client"].post(
        "/api/v1/chats",
        json={"class_id": context["class_id"], "user": "authenticated", "title": "bad payload"},
    )
    assert invalid_user_response.status_code == 400
    assert invalid_user_response.get_json()["error"]["message"] == "user_id must be an integer"


def test_chat_ai_interaction_access_for_owner_instructor_and_active_enrollment(app):
    context = _seed_chat_context(app)
    chat_id = context["chat_id"]

    owner_response = context["owner_client"].get(f"/api/v1/chats/{chat_id}/ai/interactions")
    instructor_response = context["instructor_client"].get(f"/api/v1/chats/{chat_id}/ai/interactions")
    peer_response = context["peer_client"].get(f"/api/v1/chats/{chat_id}/ai/interactions")

    assert owner_response.status_code == 200
    assert instructor_response.status_code == 200
    assert peer_response.status_code == 200

    payload = owner_response.get_json()
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["chat_id"] == chat_id
    assert payload[0]["provider"] == "mock_json"


def test_chat_ai_interaction_access_denies_dropped_or_non_enrolled_users(app):
    context = _seed_chat_context(app)
    chat_id = context["chat_id"]

    dropped_response = context["dropped_client"].get(f"/api/v1/chats/{chat_id}/ai/interactions")
    outsider_response = context["outsider_client"].get(f"/api/v1/chats/{chat_id}/ai/interactions")

    assert dropped_response.status_code == 403
    assert dropped_response.get_json()["error"]["code"] == "forbidden"
    assert dropped_response.get_json()["error"]["message"] == "access denied"

    assert outsider_response.status_code == 403
    assert outsider_response.get_json()["error"]["code"] == "forbidden"
    assert outsider_response.get_json()["error"]["message"] == "access denied"
