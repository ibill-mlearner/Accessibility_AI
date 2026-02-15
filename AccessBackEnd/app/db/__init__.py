from __future__ import annotations

from flask import Flask

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

    repositories = {
        "users": UserRepository(runtime.models["user"]),
        "ai_interactions": AIInteractionRepository(runtime.models["ai_interaction"]),
    }
    return runtime, repositories


def init_standalone_schema(runtime: StandaloneDatabase) -> None:
    """Explicit schema initialization for standalone DB runtimes."""

    runtime.create_schema()


def init_flask_database(app: Flask) -> None:
    """Explicitly create Flask-SQLAlchemy tables for the configured app DB."""

    from .. import models  # noqa: F401  # ensure model metadata is registered
    from ..extensions import db

    with app.app_context():
        db.create_all()


__all__ = [
    "AIInteractionRepository",
    "DatabaseConfig",
    "StandaloneDatabase",
    "UserRepository",
    "create_json_backed_db",
    "init_flask_database",
    "init_standalone_schema",
    "resolve_database_url",
    "create_standalone_db",
]
