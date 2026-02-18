"""
base.py sets up the database so we have a stateful repository for data with a single entry point


"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


SchemaProvider = Callable[[], tuple[type, dict[str, type]]]

#type[T] concept for url inheritance
# need to overwrite so it does not default to memory
# leave base during development though or refactoring
@dataclass(frozen=True)
class DatabaseConfig:
    """Configuration for standalone database bootstrap."""

    database_url: str = "sqlite+pysqlite:///:memory:"
    echo: bool = False


class StandaloneDatabase:
    """Small standalone DB runtime independent from Flask app wiring."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._ensure_sqlite_database_file(config.database_url)
        # sqlalchey setup, basic class control for stateful DB
        self.engine: Engine = create_engine(config.database_url, echo=config.echo, future=True)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        self.base = None
        self.models: dict[str, type] = {}

    @staticmethod
    def _ensure_sqlite_database_file(database_url: str) -> None:
        """Create file-backed SQLite targets before engine bootstraps."""

        url = make_url(database_url)
        if not url.drivername.startswith("sqlite"):
            return

        # memory early exit check
        database = url.database
        if database in {None, "", ":memory:"}:
            return

        db_path = Path(database).expanduser()
        if not db_path.is_absolute():
            # For relative sqlite URLs, the .db file is created under the current
            # working directory where the backend process is started.
            db_path = Path.cwd() / db_path

        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch(exist_ok=True)

    def bind_schema(self, schema_provider: SchemaProvider) -> None: #set
        """Load schema from a separate module/function and bind to this runtime."""

        base, models = schema_provider()
        self.base = base
        self.models = models

    def create_schema(self) -> None: #set
        """Create all bound tables."""

        if self.base is None:
            raise RuntimeError("schema provider must be bound before create_schema")
        self.base.metadata.create_all(self.engine)

    def drop_schema(self) -> None: #delete
        """Drop all bound tables."""

        if self.base is None:
            raise RuntimeError("schema provider must be bound before drop_schema")
        self.base.metadata.drop_all(self.engine)

    @contextmanager
    def session_scope(self) -> Iterator[Session]: #get
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
