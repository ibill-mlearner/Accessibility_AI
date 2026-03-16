from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine import make_url

DEFAULT_SQLITE_FILENAME = "accessibility_ai.db"


def _normalize_sqlite_url(configured: str, *, instance_path: str) -> str:
    parsed = make_url(configured)
    if not parsed.drivername.startswith("sqlite"):
        return configured

    sqlite_path = parsed.database
    if not sqlite_path or sqlite_path == ":memory:" or sqlite_path.startswith("file:"):
        return configured

    #todo: review this later, i think the path is too static to my own system
    # normalized = Path(sqlite_path).expanduser() OLD LOGIC

    normalized_path = sqlite_path
    if sqlite_path.startswith("~"):
        home_override = os.getenv("HOME")
        if home_override and (
            sqlite_path == "~" or sqlite_path.startswith("~/") or sqlite_path.startswith("~\\")
        ):
            relative = sqlite_path[1:].lstrip("/\\")
            normalized_path = str(Path(home_override) / relative) if relative else home_override

    normalized = Path(normalized_path).expanduser()

    if not normalized.is_absolute():
        normalized = Path(instance_path) / normalized

    normalized.parent.mkdir(parents=True, exist_ok=True)
    resolved = normalized.resolve().as_posix()
    return parsed.set(database=resolved).render_as_string(hide_password=False)


def resolve_database_url(
    *,
    instance_path: str,
    configured_url: str | None = None,
    env_var: str = "DATABASE_URL",
) -> str:
    """Resolve a deterministic SQLAlchemy URL for Flask runtimes.

    Resolution order:
    1) ``DATABASE_URL`` environment variable.
    2) Explicit configured URL (from config profile / tests).
    3) Persistent SQLite file inside Flask's instance path.
    """

    configured = os.getenv(env_var) or configured_url
    if configured:
        return _normalize_sqlite_url(configured, instance_path=instance_path)

    default_sqlite = Path(instance_path) / DEFAULT_SQLITE_FILENAME
    default_sqlite.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{default_sqlite.resolve().as_posix()}"
