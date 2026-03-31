from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url

from app import build_ai_service, create_app
from app.db import init_flask_database

INSTANCE_DIR = Path(__file__).resolve().parent / "instance"
SEED_SQL_FILES: tuple[Path, ...] = (
    INSTANCE_DIR / "seed_users.sql",
    INSTANCE_DIR / "seed_accommodations.sql",
    INSTANCE_DIR / "seed_user_accessibility_features.sql",
    INSTANCE_DIR / "seed_ai_models.sql",
    INSTANCE_DIR / "seed_classes.sql",
    INSTANCE_DIR / "seed_user_class_enrollments.sql",
    INSTANCE_DIR / "seed_chats.sql",
    INSTANCE_DIR / "seed_ai_interactions.sql",
)

DEBUG_TRUE_VALUES = {"1", "true", "yes", "on"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Accessibility AI backend")
    parser.add_argument("--config", choices=["development", "testing", "production"], help="Application config profile")
    parser.add_argument(
        "--ai-provider",
        choices=["live_agent", "ollama", "huggingface"],
        help=(
            "AI provider mode. Defaults to HuggingFace runtime; use ollama for local endpoint-based inference, "
            "or live_agent for external HTTP providers."
        ),
    )
    parser.add_argument("--ai-endpoint", help="AI endpoint URL override (required for --ai-provider=ollama or --ai-provider=live_agent)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables before starting the server")
    parser.add_argument("--init-only", action="store_true", help="Run one-time initialization flow and exit without starting the server")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.ai_provider in {"live_agent", "ollama"} and not args.ai_endpoint:
        raise SystemExit("--ai-endpoint is required when --ai-provider is ollama or live_agent")


def sqlite_database_path(database_uri: str) -> Path | None:
    parsed = make_url(database_uri)
    if not parsed.drivername.startswith("sqlite"):
        return None

    sqlite_db = parsed.database
    if not sqlite_db or sqlite_db == ":memory:" or sqlite_db.startswith("file:"):
        return None

    return Path(sqlite_db)


def is_debug_env_enabled() -> bool:
    return os.environ.get("DEBUG", "").strip().lower() in DEBUG_TRUE_VALUES


def seed_all_from_sql(database_uri: str) -> bool:
    database_path = sqlite_database_path(database_uri)
    if database_path is None:
        print("Skipping seed prompt: SQL seeds currently support only file-based SQLite databases.")
        return False

    scripts_applied = 0
    try:
        with sqlite3.connect(database_path.as_posix()) as conn:
            for seed_file in SEED_SQL_FILES:
                conn.executescript(seed_file.read_text(encoding="utf-8"))
                scripts_applied += 1
    except Exception as exc:
        print(f"Seed script failed after {scripts_applied}/{len(SEED_SQL_FILES)} scripts: {exc}")
        if is_debug_env_enabled():
            import traceback

            traceback.print_exc()
        print("Error in seed files. Skipping baseline seed data.")
        return False

    print("Seeded baseline data.")
    return True



def should_run_init_db_for_process(app) -> bool:
    """Run `--init-db` once per startup, including non-reloader debug runs.

    In debug mode with the Werkzeug reloader, parent process exports
    `WERKZEUG_RUN_MAIN=false` and child exports `WERKZEUG_RUN_MAIN=true`.
    If the variable is missing entirely, we are in a non-reloader process and
    should run init work normally.
    """

    if not app.debug:
        return True

    reloader_flag = os.environ.get("WERKZEUG_RUN_MAIN")
    if reloader_flag is None:
        return True
    return reloader_flag == "true"


def apply_runtime_ai_overrides(app, args: argparse.Namespace) -> None:
    if args.ai_provider:
        app.config["AI_PROVIDER"] = args.ai_provider

    if args.ai_endpoint:
        if app.config["AI_PROVIDER"] in {"ollama", "ollama_local"}:
            app.config["AI_OLLAMA_ENDPOINT"] = args.ai_endpoint
        elif app.config["AI_PROVIDER"] in {"live", "live_agent", "http"}:
            app.config["AI_LIVE_ENDPOINT"] = args.ai_endpoint

    app.extensions["ai_service"] = build_ai_service(app)


def run_init_db_flow(app) -> None:
    if not should_run_init_db_for_process(app):
        print("--init-db detected but skipped in reloader parent process.")
        return

    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]

    print(f"Resolved SQLALCHEMY_DATABASE_URI: {database_uri}")
    print("--init-db requested: running schema creation (create_all).")
    init_flask_database(app)
    print("Schema creation completed.")

    print("Running baseline seed scripts.")
    seed_ran = seed_all_from_sql(database_uri)
    print(f"Seed scripts {'ran' if seed_ran else 'did not run'}.")


def build_runtime_app(args: argparse.Namespace):
    validate_args(args)
    app = create_app(args.config)
    apply_runtime_ai_overrides(app, args)

    if args.init_db:
        run_init_db_flow(app)

    return app


def main() -> None:
    args = build_parser().parse_args()
    runtime_app = build_runtime_app(args)
    if args.init_only:
        return
    runtime_app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
