from __future__ import annotations

from sqlalchemy import inspect, text

from app import create_app
from app.db import ensure_sqlite_compat_schema, init_flask_database
from app.extensions import db


def test_init_flask_database_creates_flask_and_standalone_tables(tmp_path):
    db_path = tmp_path / "init.db"
    app = create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    with app.app_context():
        db.drop_all()

    init_flask_database(app)

    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())

    assert {"users", "chats", "messages"}.issubset(tables)


def test_ensure_sqlite_compat_schema_adds_legacy_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    app = create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text("CREATE TABLE classes (id INTEGER PRIMARY KEY, name TEXT, description TEXT, instructor_id INTEGER)"))
            conn.execute(text("CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT, model TEXT, class_id INTEGER, user_id INTEGER)"))

    ensure_sqlite_compat_schema(app)

    with app.app_context():
        inspector = inspect(db.engine)
        classes_columns = {column["name"] for column in inspector.get_columns("classes")}
        chats_columns = {column["name"] for column in inspector.get_columns("chats")}

    assert "active" in classes_columns
    assert "ai_interaction_id" in chats_columns
