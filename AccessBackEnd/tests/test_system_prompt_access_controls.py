import pytest

from ..app.db import init_flask_database
from ..app.extensions import db
from ..app.models import Accommodation, AccommodationSystemPrompt, CourseClass, SystemPrompt, User


@pytest.fixture(autouse=True)
def _db_schema(app):
    with app.app_context():
        init_flask_database(app)
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def users(app):
    with app.app_context():
        admin = User(email="admin@example.com", role="admin")
        admin.set_password("Password123!")

        owner_instructor = User(email="owner@example.com", role="instructor")
        owner_instructor.set_password("Password123!")

        other_instructor = User(email="other@example.com", role="instructor")
        other_instructor.set_password("Password123!")

        student = User(email="student@example.com", role="student")
        student.set_password("Password123!")

        db.session.add_all([admin, owner_instructor, other_instructor, student])
        db.session.commit()

        return {
            "admin": {"id": admin.id, "email": admin.email, "password": "Password123!"},
            "owner": {"id": owner_instructor.id, "email": owner_instructor.email, "password": "Password123!"},
            "other": {"id": other_instructor.id, "email": other_instructor.email, "password": "Password123!"},
            "student": {"id": student.id, "email": student.email, "password": "Password123!"},
        }


@pytest.fixture()
def classes(app, users):
    with app.app_context():
        owner_class = CourseClass(
            name="Owner Class",
            description="Owned by instructor",
            instructor_id=users["owner"]["id"],
            active=True,
        )
        other_class = CourseClass(
            name="Other Class",
            description="Owned by someone else",
            instructor_id=users["other"]["id"],
            active=True,
        )
        db.session.add_all([owner_class, other_class])
        db.session.commit()

        return {"owner_class_id": owner_class.id, "other_class_id": other_class.id}


@pytest.fixture()
def prompts(app, users, classes):
    with app.app_context():
        owner_prompt = SystemPrompt(
            class_id=classes["owner_class_id"],
            instructor_id=users["owner"]["id"],
            text="Owner prompt",
        )
        owner_prompt_two = SystemPrompt(
            class_id=classes["owner_class_id"],
            instructor_id=users["owner"]["id"],
            text="Owner prompt two",
        )
        other_prompt = SystemPrompt(
            class_id=classes["other_class_id"],
            instructor_id=users["other"]["id"],
            text="Other prompt",
        )
        db.session.add_all([owner_prompt, owner_prompt_two, other_prompt])
        db.session.commit()

        return {
            "owner_prompt_id": owner_prompt.id,
            "owner_prompt_two_id": owner_prompt_two.id,
            "other_prompt_id": other_prompt.id,
        }


@pytest.fixture()
def accommodation(app):
    with app.app_context():
        record = Accommodation(title="Extra time", details="extended time", active=True)
        db.session.add(record)
        db.session.commit()
        return {"accommodation_id": record.id}


@pytest.fixture()
def existing_link(app, accommodation, prompts):
    with app.app_context():
        link = AccommodationSystemPrompt(
            accommodation_id=accommodation["accommodation_id"],
            system_prompt_id=prompts["owner_prompt_id"],
        )
        db.session.add(link)
        db.session.commit()
        return {"existing_link_id": link.id}


def _login(client, user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200


def test_system_prompt_create_forbidden_for_student(client, users, classes):
    _login(client, users["student"])

    response = client.post(
        "/api/v1/system-prompts",
        json={"class_id": classes["owner_class_id"], "text": "new prompt"},
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"] == "forbidden"
    assert payload["current_role"] == "student"
    assert payload["required_roles"] == ["admin", "instructor"]


def test_system_prompt_owner_can_create(client, users, classes):
    _login(client, users["owner"])

    response = client.post(
        "/api/v1/system-prompts",
        json={
            "class_id": classes["owner_class_id"],
            "instructor_id": users["owner"]["id"],
            "text": "owned prompt",
        },
    )

    assert response.status_code == 201


def test_system_prompt_non_owner_forbidden_update(client, users, prompts, classes):
    _login(client, users["other"])

    response = client.patch(
        f"/api/v1/system-prompts/{prompts['owner_prompt_id']}",
        json={"text": "should fail"},
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"] == "forbidden"
    assert payload["details"]["action"] == "update"
    assert payload["details"]["class_id"] == classes["owner_class_id"]
    assert payload["details"]["current_role"] == "instructor"


def test_system_prompt_admin_allowed_delete(client, users, prompts):
    _login(client, users["admin"])

    response = client.delete(f"/api/v1/system-prompts/{prompts['other_prompt_id']}")

    assert response.status_code == 200
    assert response.get_json()["id"] == prompts["other_prompt_id"]


def test_link_create_forbidden_for_student(client, users, accommodation, prompts):
    _login(client, users["student"])

    response = client.post(
        "/api/v1/accommodation-system-prompt-links",
        json={
            "accommodation_id": accommodation["accommodation_id"],
            "system_prompt_id": prompts["owner_prompt_two_id"],
        },
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"] == "forbidden"
    assert payload["current_role"] == "student"
    assert payload["required_roles"] == ["admin", "instructor"]


def test_link_owner_can_create(client, users, accommodation, prompts):
    _login(client, users["owner"])

    response = client.post(
        "/api/v1/accommodation-system-prompt-links",
        json={
            "accommodation_id": accommodation["accommodation_id"],
            "system_prompt_id": prompts["owner_prompt_two_id"],
        },
    )

    assert response.status_code == 201


def test_link_non_owner_forbidden_delete(client, users, accommodation, prompts):
    _login(client, users["owner"])
    created = client.post(
        "/api/v1/accommodation-system-prompt-links",
        json={
            "accommodation_id": accommodation["accommodation_id"],
            "system_prompt_id": prompts["owner_prompt_two_id"],
        },
    )
    assert created.status_code == 201
    link_id = created.get_json()["id"]

    _login(client, users["other"])
    forbidden = client.delete(f"/api/v1/accommodation-system-prompt-links/{link_id}")

    assert forbidden.status_code == 403
    payload = forbidden.get_json()
    assert payload["error"] == "forbidden"
    assert payload["details"]["action"] == "delete"
    assert payload["details"]["current_role"] == "instructor"


def test_link_admin_allowed_delete(client, users, existing_link):
    _login(client, users["admin"])

    response = client.delete(
        f"/api/v1/accommodation-system-prompt-links/{existing_link['existing_link_id']}"
    )

    assert response.status_code == 200
    assert response.get_json()["id"] == existing_link["existing_link_id"]


def test_integration_owner_lifecycle_and_non_owner_blocked(client, users, classes, accommodation):
    _login(client, users["owner"])

    create_prompt = client.post(
        "/api/v1/system-prompts",
        json={
            "class_id": classes["owner_class_id"],
            "instructor_id": users["owner"]["id"],
            "text": "integration prompt",
        },
    )
    assert create_prompt.status_code == 201
    prompt_id = create_prompt.get_json()["id"]

    create_link = client.post(
        "/api/v1/accommodation-system-prompt-links",
        json={
            "accommodation_id": accommodation["accommodation_id"],
            "system_prompt_id": prompt_id,
        },
    )
    assert create_link.status_code == 201
    link_id = create_link.get_json()["id"]

    update_prompt = client.patch(
        f"/api/v1/system-prompts/{prompt_id}",
        json={"text": "integration prompt updated"},
    )
    assert update_prompt.status_code == 200

    _login(client, users["other"])
    forbidden_delete = client.delete(f"/api/v1/accommodation-system-prompt-links/{link_id}")
    assert forbidden_delete.status_code == 403

    _login(client, users["owner"])
    delete_link = client.delete(f"/api/v1/accommodation-system-prompt-links/{link_id}")
    assert delete_link.status_code == 200

    delete_prompt = client.delete(f"/api/v1/system-prompts/{prompt_id}")
    assert delete_prompt.status_code == 200