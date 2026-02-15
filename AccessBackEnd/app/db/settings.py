from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SQLITE_FILE = Path("AccessBackEnd") / "var" / "accessibility_ai.db"


def resolve_database_url(env_var: str = "DATABASE_URL") -> str:
    """Resolve the SQLAlchemy URL from env with a persistent SQLite fallback."""

    return os.getenv(env_var, f"sqlite:///{DEFAULT_SQLITE_FILE.as_posix()}")

