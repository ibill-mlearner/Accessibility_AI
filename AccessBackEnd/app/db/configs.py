from __future__ import annotations

from dataclasses import dataclass

from app.utils.env_config import parse_env


@dataclass(slots=True)
class DBModuleConfig:
    sqlalchemy_database_uri: str | None = None
    migrations_dir: str = "migrations"

    @classmethod
    def from_env(cls) -> "DBModuleConfig":
        return cls(
            sqlalchemy_database_uri=parse_env("SQLALCHEMY_DATABASE_URI"),
            migrations_dir=parse_env("MIGRATIONS_DIR", "migrations"),
        )

    def summary(self) -> dict[str, str]:
        return {"section": "db", "has_uri": str(bool(self.sqlalchemy_database_uri)).lower()}
