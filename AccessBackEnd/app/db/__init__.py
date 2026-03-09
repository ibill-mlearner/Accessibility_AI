from __future__ import annotations
from pathlib import Path
from collections.abc import Iterable

from flask import Flask
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from interfaces import AIInteractionRepositoryInterface, UserRepositoryInterface
from ..models.db_schema import get_schema_bundle
from .base import DatabaseConfig, StandaloneDatabase
from .json_backend import create_json_backed_db
from .repositories import AIInteractionRepository, UserRepository
from .settings import resolve_database_url


def create_standalone_db(
    *,
    database_url: str | None = None,
    echo: bool = False,
    create_schema: bool = False,
):
    """Create an app-agnostic DB runtime with repositories and schema bound."""

    resolved_url = database_url or "sqlite:///:memory:"
    runtime = StandaloneDatabase(DatabaseConfig(database_url=resolved_url, echo=echo))
    runtime.bind_schema(get_schema_bundle)
    if create_schema:
        runtime.create_schema()

        repositories: dict[str, UserRepositoryInterface | AIInteractionRepositoryInterface] = {
        "users": UserRepository(runtime.models["user"]),
        "ai_interactions": AIInteractionRepository(runtime.models["ai_interaction"]),
    }
    return runtime, repositories


def init_standalone_schema(runtime: StandaloneDatabase) -> None:
    """Explicit schema initialization for standalone DB runtimes."""

    runtime.create_schema()
def _run_sqlite_ai_models_migration(app: Flask) -> None:
    """Apply ai_models provider/model_id migration for legacy SQLite databases."""

    from ..extensions import db

    migration_script = Path(__file__).resolve().parent / "migrations" / "sqlite_ai_models_provider_model_id.sql"
    if not migration_script.exists():
        app.logger.warning("AI model migration script missing at %s", migration_script)
        return

    with app.app_context():
        engine = db.engine
        if engine.dialect.name != "sqlite":
            return

        inspector = inspect(engine)
        if "ai_models" not in set(inspector.get_table_names()):
            return

        columns = {column["name"] for column in inspector.get_columns("ai_models")}
        if "model_id" in columns:
            return

        script = migration_script.read_text(encoding="utf-8")
        statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]
        try:
            with engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                for statement in statements:
                    conn.execute(text(statement))
                conn.execute(text("PRAGMA foreign_keys=ON"))
        except SQLAlchemyError as exc:
            app.logger.warning("Unable to migrate ai_models provider/model_id schema: %s", exc)

def init_flask_database(app: Flask) -> None:
    """Explicitly create every configured SQLAlchemy table set for the app DB."""

    from .. import models  # noqa: F401  # ensure model metadata is registered
    from ..extensions import db
    from ..models.base import Base

    with app.app_context():
        db.create_all()
        Base.metadata.create_all(bind=db.engine)


def _sqlite_has_column(engine, table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def ensure_sqlite_compat_schema(app: Flask) -> None:
    """Best-effort compatibility patching for legacy SQLite files missing new columns."""

    from ..extensions import db
    _run_sqlite_ai_models_migration(app)
    column_updates: Iterable[tuple[str, str, str]] = (
        ("classes", "active", "BOOLEAN NOT NULL DEFAULT 1"),
        ("chats", "ai_interaction_id", "INTEGER"),
    )

    with app.app_context():
        engine = db.engine
        if engine.dialect.name != "sqlite":
            return

        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        for table_name, column_name, ddl in column_updates:
            if table_name not in existing_tables:
                continue
            if _sqlite_has_column(engine, table_name, column_name):
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
            except SQLAlchemyError as exc:
                app.logger.warning(
                    "Unable to patch legacy sqlite schema for %s.%s: %s",
                    table_name,
                    column_name,
                    exc,
                )


__all__ = [
    "AIInteractionRepository",
    "DatabaseConfig",
    "StandaloneDatabase",
    "UserRepository",
    "create_json_backed_db",
    "ensure_sqlite_compat_schema",
    "init_flask_database",
    "init_standalone_schema",
    "resolve_database_url",
    "create_standalone_db",
    "UserRepositoryInterface",
    "AIInteractionRepositoryInterface"
]
