"""SQLAlchemy-backed repository for standalone user-account persistence.

This repository intentionally centralizes the normalization and lookup rules for
emails so auth and service layers can rely on one consistent data-access path.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..interfaces import UserRepositoryInterface
import hashlib


class UserRepository(UserRepositoryInterface):
    """Persistence helpers for standalone DB user records."""

    def __init__(self, user_model: type):
        """Store the SQLAlchemy user model class used by CRUD helpers."""
        self.user_model = user_model

    def create(self, session: Session, *, email: str, password_hash: str, role: str = "student"):
        """Create a user row with normalized email defaults and transitional identity metadata."""
        normalized_email = email.lower().strip()
        user = self.user_model(
            email=normalized_email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            role=role,
            email_confirmed=False,
            access_failed_count=0,
            lockout_enabled=True,
            lockout_end=None,
            security_stamp=f"transitional-{hashlib.sha256(normalized_email.encode('utf-8')).hexdigest()[:32]}",
            last_login_at=None,
        )
        session.add(user)
        session.flush()
        return user

    def get_by_id(self, session: Session, user_id: int):
        """Fetch one user by primary key, returning `None` when absent."""
        return session.get(self.user_model, user_id)

    def get_by_email(self, session: Session, email: str):
        """Find a user by normalized-email fallback logic for backward-compatible account lookups."""
        normalized_email = email.lower().strip()
        statement = select(self.user_model).where(
            or_(
                self.user_model.normalized_email == normalized_email,
                self.user_model.email == normalized_email,
            )
        )
        return session.scalars(statement).first()
