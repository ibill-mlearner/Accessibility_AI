from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app import create_app
from app import config as app_config
from app.db import create_json_backed_db, create_standalone_db
from app.models.entity_metadata import get_entity_metadata_bundle


def test_create_standalone_db_binds_schema_and_repositories():
    runtime, repositories = create_standalone_db()

    assert runtime.base is not None
    assert "user" in runtime.models
    assert set(repositories.keys()) == {"users", "ai_interactions"}


def test_standalone_db_user_and_interaction_roundtrip():
    runtime, repositories = create_standalone_db()

    with runtime.session_scope() as session:
        user = repositories["users"].create(
            session,
            email="Student@One.Example",
            password_hash="hashed-password",
            role="student",
        )
        repositories["ai_interactions"].create(
            session,
            prompt="Summarize ATP synthesis",
            response_text="ATP synthesis primarily occurs in the mitochondria.",
            provider="mock_json",
            chat_id=None,
        )
        user_id = user.id

    with runtime.session_scope() as session:
        loaded_user = repositories["users"].get_by_id(session, user_id)
        loaded_by_email = repositories["users"].get_by_email(session, "student@one.example")

    assert loaded_user is not None
    assert loaded_user.email == "student@one.example"
    assert loaded_by_email is not None
    assert loaded_by_email.id == loaded_user.id


def test_json_data_source_can_replace_sql_runtime_for_repo_contract():
    seed_path = Path(__file__).parent / "resources" / "modular_db_seed.json"
    runtime, repositories = create_json_backed_db(
        json_path=seed_path.as_posix(),
        metadata_provider=get_entity_metadata_bundle,
    )

    with runtime.session_scope() as session:
        seeded_user = repositories["users"].get_by_email(session, "json.user@example.com")
        created = repositories["users"].create(
            session,
            email="new.user@example.com",
            password_hash="new-hash",
            role="instructor",
        )

    assert seeded_user is not None
    assert seeded_user.role == "student"
    assert created.id == 2


def test_create_app_can_mount_external_data_backend_in_two_lines(monkeypatch):
    seed_path = Path(__file__).parent / "resources" / "modular_db_seed.json"
    app_config.TestingConfig.DATA_BACKEND_FACTORY = lambda: create_json_backed_db(
        json_path=seed_path.as_posix(),
        metadata_provider=get_entity_metadata_bundle,
    )

    app = create_app("testing")

    assert "data_backend" in app.extensions
    runtime, repositories = app.extensions["data_backend"]
    with runtime.session_scope() as session:
        user = repositories["users"].get_by_email(session, "json.user@example.com")
    assert user is not None

    monkeypatch.setattr(app_config.TestingConfig, "DATA_BACKEND_FACTORY", None)


def test_create_standalone_db_creates_missing_sqlite_file_and_schema(tmp_path):
    db_path = tmp_path / "runtime" / "bootstrap.db"

    assert not db_path.exists()

    runtime, _repositories = create_standalone_db(
        database_url=f"sqlite+pysqlite:///{db_path.as_posix()}"
    )

    assert db_path.exists()
    with runtime.session_scope() as session:
        users_table = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        ).scalar_one_or_none()

    assert users_table == "users"
