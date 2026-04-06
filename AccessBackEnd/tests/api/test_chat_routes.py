import os
os.environ.setdefault("TEST_AI_PROVIDER", "ollama")

from app.db import init_flask_database
from app.extensions import db
from app.models import Chat, CourseClass, User


def _register(client, *, email: str, password: str = "Password123!", role: str = "instructor"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert response.status_code == 201


def _seed_owned_class_for_user(user_email: str) -> int:
    user = db.session.query(User).filter(User.email == user_email).first()
    assert user is not None
    class_record = CourseClass(
        name="Biology 101",
        description="Foundations",
        instructor_id=int(user.id),
        active=True,
    )
    db.session.add(class_record)
    db.session.commit()
    return int(class_record.id)


def test_chat_archive_hides_chat_from_list(app, client):
    with app.app_context():
        init_flask_database(app)

    email = "chat-archive@example.com"
    _register(client, email=email)

    with app.app_context():
        class_id = _seed_owned_class_for_user(email)

    create_response = client.post(
        "/api/v1/chats",
        json={"class_id": class_id, "title": "Intro chat", "model": "test-model"},
    )
    assert create_response.status_code == 201
    payload = create_response.get_json()
    chat_id = int(payload["id"])
    assert payload["active"] is True

    archive_response = client.patch(f"/api/v1/chats/{chat_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.get_json()["active"] is False

    list_response = client.get("/api/v1/chats")
    assert list_response.status_code == 200
    assert list_response.get_json() == []

    with app.app_context():
        archived_chat = db.session.get(Chat, chat_id)
        assert archived_chat is not None
        assert archived_chat.active is False


def test_edit_title_enforces_20_word_limit(app, client):
    with app.app_context():
        init_flask_database(app)

    email = "chat-edit-title@example.com"
    _register(client, email=email)

    with app.app_context():
        class_id = _seed_owned_class_for_user(email)

    create_response = client.post(
        "/api/v1/chats",
        json={"class_id": class_id, "title": "Short title", "model": "test-model"},
    )
    assert create_response.status_code == 201
    chat_id = int(create_response.get_json()["id"])

    ok_title = "One two three four five six seven eight nine ten"
    edit_response = client.patch(
        f"/api/v1/chats/{chat_id}/edit-title",
        json={"title": ok_title},
    )
    assert edit_response.status_code == 200
    assert edit_response.get_json()["title"] == ok_title

    too_long_title = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone"
    invalid_response = client.patch(
        f"/api/v1/chats/{chat_id}/edit-title",
        json={"title": too_long_title},
    )
    assert invalid_response.status_code == 400
    assert "at most 20 words" in invalid_response.get_json()["error"]["message"]
