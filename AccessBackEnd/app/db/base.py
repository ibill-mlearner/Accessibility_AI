from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


SchemaProvider = Callable[[], tuple[type, dict[str, type]]]


@dataclass(frozen=True)
class DatabaseConfig:
    """Configuration for standalone database bootstrap."""

    database_url: str = "sqlite+pysqlite:///:memory:"
    echo: bool = False


class StandaloneDatabase:
    """Small standalone DB runtime independent from Flask app wiring."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Engine = create_engine(config.database_url, echo=config.echo, future=True)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        self.base = None
        self.models: dict[str, type] = {}

    def bind_schema(self, schema_provider: SchemaProvider) -> None:
        """Load schema from a separate module/function and bind to this runtime."""

        base, models = schema_provider()
        self.base = base
        self.models = models

    def create_schema(self) -> None:
        """Create all bound tables."""

        if self.base is None:
            raise RuntimeError("schema provider must be bound before create_schema")
        self.base.metadata.create_all(self.engine)

    def drop_schema(self) -> None:
        """Drop all bound tables."""

        if self.base is None:
            raise RuntimeError("schema provider must be bound before drop_schema")
        self.base.metadata.drop_all(self.engine)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Unit-of-work style transactional scope."""

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
