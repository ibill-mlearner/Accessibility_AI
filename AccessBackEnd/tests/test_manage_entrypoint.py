from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path



MANAGE_PATH = Path(__file__).resolve().parents[1] / "manage.py"


def test_manage_import_has_no_cli_side_effects(monkeypatch):
    monkeypatch.setenv("APP_CONFIG", "testing")
    monkeypatch.setattr("sys.argv", ["manage.py", "--unknown-flag"])

    spec = importlib.util.spec_from_file_location("backend_manage_module", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert module.app is not None


def test_seed_users_from_sql_inserts_rows(tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_seed", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "seed-test.db"
    uri = f"sqlite:///{db_path.as_posix()}"
    module._SEED_USERS_SQL = Path(__file__).resolve().parents[1] / "instance" / "seed_users.sql"

    import sqlite3

    with sqlite3.connect(db_path.as_posix()) as conn:
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE classes (id INTEGER PRIMARY KEY, role TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT NOT NULL, started_at TEXT DEFAULT CURRENT_TIMESTAMP, model TEXT NOT NULL, class_id INTEGER NOT NULL, user_id INTEGER NOT NULL)"
        )

    assert module._seed_users_from_sql(uri)

    with sqlite3.connect(db_path.as_posix()) as conn:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        chat_count = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]

    assert user_count == 4
    assert chat_count == 3


def test_build_runtime_app_first_run_prompts_for_seed(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_runtime", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "first-run.db"
    args = Namespace(
        config="testing",
        ai_provider=None,
        ai_endpoint=None,
        host="0.0.0.0",
        port=5000,
        init_db=True,
    )

    prompted = {"called": False}

    def _prompt(database_uri: str) -> None:
        prompted["called"] = True
        assert database_uri == f"sqlite+pysqlite:///{db_path.as_posix()}"

    app = module.create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    monkeypatch.setattr(module, "create_app", lambda _config: app)
    monkeypatch.setattr(module, "_prompt_for_seed_users", _prompt)

    module.build_runtime_app(args)

    assert prompted["called"] is True


def test_prompt_for_seed_users_skips_non_interactive(monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("backend_manage_module_prompt", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: False)

    module._prompt_for_seed_users("sqlite:////tmp/example.db")
    out = capsys.readouterr().out
    assert "Skipping interactive seed prompt" in out
