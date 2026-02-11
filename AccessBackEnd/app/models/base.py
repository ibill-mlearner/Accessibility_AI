from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Standalone SQLAlchemy declarative base used by the app/db package."""
