from __future__ import annotations

from ..models.db_schema import get_schema_bundle
from .base import DatabaseConfig, StandaloneDatabase
from .json_backend import create_json_backed_db
from .repositories import AIInteractionRepository, UserRepository


def create_standalone_db(
    *,
    database_url: str = "sqlite+pysqlite:///:memory:",
    echo: bool = False,
):
    """Create an app-agnostic DB runtime with repositories and schema bound."""

    runtime = StandaloneDatabase(DatabaseConfig(database_url=database_url, echo=echo))
    runtime.bind_schema(get_schema_bundle)
    runtime.create_schema()

    repositories = {
        "users": UserRepository(runtime.models["user"]),
        "ai_interactions": AIInteractionRepository(runtime.models["ai_interaction"]),
    }
    return runtime, repositories


__all__ = [
    "AIInteractionRepository",
    "DatabaseConfig",
    "StandaloneDatabase",
    "UserRepository",
    "create_json_backed_db",
    "create_standalone_db",
]
