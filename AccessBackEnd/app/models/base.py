"""Declarative base definition for ORM tables.

Table map:
- No table declared here; this file provides the shared SQLAlchemy `Base` class used by model files.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Standalone SQLAlchemy declarative base used by the app/db package."""
