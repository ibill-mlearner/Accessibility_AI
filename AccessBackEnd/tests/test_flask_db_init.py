from __future__ import annotations

from sqlalchemy import inspect

from app import create_app
from app.db import init_flask_database
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

