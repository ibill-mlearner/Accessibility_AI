from __future__ import annotations

import os
from pathlib import Path

from .utilities import DatabaseSettingsUtilities

DEFAULT_SQLITE_FILENAME = "accessibility_ai.db"


class DatabaseSettings:
    def __init__(
        self,
        *,
        instance_path: str,
        configured_url: str | None = None,
        env_var: str = "DATABASE_URL",
        sqlite_url_filename: str = DEFAULT_SQLITE_FILENAME,
    ) -> None:
        self.instance_path = instance_path
        self.configured_url = configured_url
        self.env_var = env_var
        self.sqlite_url_filename = sqlite_url_filename

    def resolve_database_url(self) -> str:
        configured = os.getenv(self.env_var) or self.configured_url
        if configured:
            return DatabaseSettingsUtilities.normalize_sqlite_url(configured, instance_path=self.instance_path)

        default_sqlite = Path(self.instance_path) / self.sqlite_url_filename
        default_sqlite.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{default_sqlite.resolve().as_posix()}"


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
    return DatabaseSettings(
        instance_path=instance_path,
        configured_url=configured_url,
        env_var=env_var,
        sqlite_url_filename=DEFAULT_SQLITE_FILENAME,
    ).resolve_database_url()
