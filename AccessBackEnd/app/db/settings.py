from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SQLITE_FILENAME = "accessibility_ai.db"


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
        if configured.startswith("sqlite:///") and not configured.startswith("sqlite:////"):
            sqlite_path = configured[len("sqlite:///") :]
            if sqlite_path and sqlite_path != ":memory:":
                normalized = Path(instance_path) / sqlite_path
                normalized.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite:///{normalized.resolve().as_posix()}"
        return configured

    default_sqlite = Path(instance_path) / DEFAULT_SQLITE_FILENAME
    default_sqlite.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{default_sqlite.resolve().as_posix()}"
