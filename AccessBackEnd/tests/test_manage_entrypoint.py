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


def test_seed_all_from_sql_can_insert_users_only_when_configured(tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_seed", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "seed-test.db"
    uri = f"sqlite:///{db_path.as_posix()}"
    module._SEED_SQL_FILES = [Path(__file__).resolve().parents[1] / "instance" / "seed_users.sql"]

    import sqlite3

    with sqlite3.connect(db_path.as_posix()) as conn:
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, normalized_email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, last_login_at TEXT, is_active INTEGER NOT NULL DEFAULT 1, email_confirmed INTEGER NOT NULL DEFAULT 0, lockout_end TEXT, access_failed_count INTEGER NOT NULL DEFAULT 0, lockout_enabled INTEGER NOT NULL DEFAULT 1, security_stamp TEXT NOT NULL DEFAULT '')"
        )
        conn.execute(
            "CREATE TABLE classes (id INTEGER PRIMARY KEY, role TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, instructor_id INTEGER NOT NULL, term TEXT, section_code TEXT, external_class_key TEXT UNIQUE)"
        )
        conn.execute(
            "CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT NOT NULL, started_at TEXT DEFAULT CURRENT_TIMESTAMP, model TEXT NOT NULL, class_id INTEGER NOT NULL, user_id INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE user_class_enrollments (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, class_id INTEGER NOT NULL, role TEXT NOT NULL, enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP, dropped_at TEXT)"
        )

    assert module._seed_all_from_sql(uri)

    with sqlite3.connect(db_path.as_posix()) as conn:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        chat_count = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]

    assert user_count == 6
    assert chat_count == 0


def test_seed_all_from_sql_runs_all_seed_scripts(tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_seed_all", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "seed-all-test.db"
    uri = f"sqlite:///{db_path.as_posix()}"

    seed_a = tmp_path / "seed_a.sql"
    seed_b = tmp_path / "seed_b.sql"
    seed_a.write_text("BEGIN TRANSACTION; CREATE TABLE IF NOT EXISTS seed_check (id INTEGER PRIMARY KEY, name TEXT); COMMIT;")
    seed_b.write_text("BEGIN TRANSACTION; INSERT INTO seed_check (name) SELECT 'ok' WHERE NOT EXISTS (SELECT 1 FROM seed_check WHERE name='ok'); COMMIT;")
    module._SEED_SQL_FILES = [seed_a, seed_b]

    assert module._seed_all_from_sql(uri)

    import sqlite3

    with sqlite3.connect(db_path.as_posix()) as conn:
        row_count = conn.execute("SELECT COUNT(*) FROM seed_check").fetchone()[0]

    assert row_count == 1


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
        seed="prompt",
    )

    prompted = {"called": False}

    def _prompt(database_uri: str) -> None:
        prompted["called"] = True
        assert database_uri == f"sqlite+pysqlite:///{db_path.as_posix()}"

    app = module.create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    monkeypatch.setattr(module, "create_app", lambda _config: app)
    monkeypatch.setattr(module, "_prompt_for_seed_users", _prompt)
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    module.build_runtime_app(args)

    assert prompted["called"] is True




def test_build_runtime_app_init_db_prompts_even_when_db_exists(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_runtime_existing_db", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "existing.db"
    db_path.write_text("")

    args = Namespace(
        config="testing",
        ai_provider=None,
        ai_endpoint=None,
        host="0.0.0.0",
        port=5000,
        init_db=True,
        seed="prompt",
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


def test_build_parser_excludes_mock_provider_choice():
    spec = importlib.util.spec_from_file_location("backend_manage_module_validate", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    parser = module._build_parser()
    provider_action = next(action for action in parser._actions if action.dest == "ai_provider")

    assert "mock_json" not in provider_action.choices
    assert set(provider_action.choices) == {"live_agent", "ollama", "huggingface"}


def test_build_runtime_app_sets_only_ollama_endpoint(monkeypatch):
    spec = importlib.util.spec_from_file_location("backend_manage_module_ollama", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    args = Namespace(
        config="testing",
        ai_provider="ollama",
        ai_endpoint="http://localhost:11434/api/chat",
        host="0.0.0.0",
        port=5000,
        init_db=False,
        seed="prompt",
    )

    app = module.build_runtime_app(args)

    assert app.config["AI_PROVIDER"] == "ollama"
    assert app.config["AI_OLLAMA_ENDPOINT"] == "http://localhost:11434/api/chat"


def test_build_runtime_app_non_interactive_new_db_auto_seeds(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_runtime_auto_seed", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "auto-seed.db"
    args = Namespace(
        config="testing",
        ai_provider=None,
        ai_endpoint=None,
        host="0.0.0.0",
        port=5000,
        init_db=True,
        seed="prompt",
    )

    app = module.create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    monkeypatch.setattr(module, "create_app", lambda _config: app)
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: False)

    seeded = {"called": False}

    def _seed(database_uri: str) -> bool:
        seeded["called"] = True
        assert database_uri == f"sqlite+pysqlite:///{db_path.as_posix()}"
        return True

    monkeypatch.setattr(module, "_seed_all_from_sql", _seed)

    module.build_runtime_app(args)

    assert seeded["called"] is True


def test_build_runtime_app_seed_never_skips_prompt_and_seed(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("backend_manage_module_runtime_seed_never", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    db_path = tmp_path / "seed-never.db"
    args = Namespace(
        config="testing",
        ai_provider=None,
        ai_endpoint=None,
        host="0.0.0.0",
        port=5000,
        init_db=True,
        seed="never",
    )

    app = module.create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{db_path.as_posix()}")

    monkeypatch.setattr(module, "create_app", lambda _config: app)

    prompted = {"called": False}
    seeded = {"called": False}

    def _prompt(_database_uri: str) -> None:
        prompted["called"] = True

    def _seed(_database_uri: str) -> bool:
        seeded["called"] = True
        return True

    monkeypatch.setattr(module, "_prompt_for_seed_users", _prompt)
    monkeypatch.setattr(module, "_seed_all_from_sql", _seed)

    module.build_runtime_app(args)

    assert prompted["called"] is False
    assert seeded["called"] is False
