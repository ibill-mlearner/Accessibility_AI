import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

from app import create_app, build_ai_service
from app.db import init_flask_database
from app.extensions import db


_INSTANCE_DIR = Path(__file__).resolve().parent / "instance"
_SEED_SQL_FILES = [
    _INSTANCE_DIR / "seed_users.sql",
    _INSTANCE_DIR / "seed_accommodations.sql",
    _INSTANCE_DIR / "seed_ai_models.sql",
    _INSTANCE_DIR / "seed_classes.sql",
    _INSTANCE_DIR / "seed_user_class_enrollments.sql",
    _INSTANCE_DIR / "seed_chats.sql",
    _INSTANCE_DIR / "seed_ai_interactions.sql",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Accessibility AI backend")
    parser.add_argument("--config", choices=["development", "testing", "production"], help="Application config profile")
    parser.add_argument(
        "--ai-provider",
        choices=["live_agent", "ollama", "huggingface"],
        help="AI provider mode. Defaults to HuggingFace runtime; use ollama for local endpoint-based inference, or live_agent for external HTTP providers.",
    )
    parser.add_argument("--ai-endpoint", help="AI endpoint URL override (required for --ai-provider=ollama or --ai-provider=live_agent)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables before starting the server")
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.ai_provider in {"live_agent", "ollama"} and not args.ai_endpoint:
        raise SystemExit("--ai-endpoint is required when --ai-provider is ollama or live_agent")



def _sqlite_database_path(database_uri: str) -> Path | None:
    parsed = make_url(database_uri)
    if not parsed.drivername.startswith("sqlite"):
        return None

    sqlite_db = parsed.database
    if not sqlite_db or sqlite_db == ":memory:" or sqlite_db.startswith("file:"):
        return None

    return Path(sqlite_db)


def _seed_users_from_sql(database_uri: str) -> bool:
    database_path = _sqlite_database_path(database_uri)
    if database_path is None:
        print("Skipping user seed prompt: SQL seed currently supports only file-based SQLite databases.")
        return False

    seed_users_sql = _SEED_SQL_FILES[0]
    if not seed_users_sql.exists():
        print(f"Skipping user seed prompt: seed file not found at {seed_users_sql}.")
        return False

    script = seed_users_sql.read_text(encoding="utf-8")
    with sqlite3.connect(database_path.as_posix()) as conn:
        conn.executescript(script)

    print(f"Seeded users from {seed_users_sql.relative_to(Path(__file__).resolve().parent)}")
    return True


def _seed_all_from_sql(database_uri: str) -> bool:
    database_path = _sqlite_database_path(database_uri)
    if database_path is None:
        print("Skipping seed prompt: SQL seeds currently support only file-based SQLite databases.")
        return False

    missing = [seed_file for seed_file in _SEED_SQL_FILES if not seed_file.exists()]
    if missing:
        missing_list = ", ".join(path.as_posix() for path in missing)
        print(f"Skipping seed prompt: seed file(s) not found: {missing_list}.")
        return False

    with sqlite3.connect(database_path.as_posix()) as conn:
        for seed_file in _SEED_SQL_FILES:
            conn.executescript(seed_file.read_text(encoding="utf-8"))

    base_dir = Path(__file__).resolve().parent

    def _display_path(seed_file: Path) -> str:
        try:
            return seed_file.relative_to(base_dir).as_posix()
        except ValueError:
            return seed_file.as_posix()

    print("Seeded baseline data from: " + ", ".join(_display_path(seed_file) for seed_file in _SEED_SQL_FILES))
    return True


def _prompt_for_seed_users(database_uri: str) -> None:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Skipping interactive seed prompt (non-interactive session).")
        return

    answer = input("Seed default baseline data now? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        print("Skipping seed data.")
        return

    _seed_all_from_sql(database_uri)


def build_runtime_app(args: argparse.Namespace):
    _validate_args(args)

    app = create_app(args.config)

    if args.ai_provider:
        app.config["AI_PROVIDER"] = args.ai_provider
    if args.ai_endpoint:
        if app.config["AI_PROVIDER"] in {"ollama", "ollama_local"}:
            app.config["AI_OLLAMA_ENDPOINT"] = args.ai_endpoint
        elif app.config["AI_PROVIDER"] in {"live", "live_agent", "http"}:
            app.config["AI_LIVE_ENDPOINT"] = args.ai_endpoint

    # Rebuild service with runtime overrides from parsed args.
    app.extensions["ai_service"] = build_ai_service(app)

    if args.init_db:
        sqlite_db_path = _sqlite_database_path(app.config["SQLALCHEMY_DATABASE_URI"])
        first_run = sqlite_db_path is not None and not sqlite_db_path.exists()
        print(f"Resolved SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        init_flask_database(app)
        if first_run:
            _prompt_for_seed_users(app.config["SQLALCHEMY_DATABASE_URI"])

    return app


app = create_app()


@app.shell_context_processor
def _shell_context():
    return {"db": db}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    runtime_app = build_runtime_app(args)
    runtime_app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
