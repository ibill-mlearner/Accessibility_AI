from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session


class UserRepository:
    """Persistence helpers for standalone DB user records."""

    def __init__(self, user_model: type):
        self.user_model = user_model

    def create(self, session: Session, *, email: str, password_hash: str, role: str = "student"):
        normalized_email = email.lower().strip()
        user = self.user_model(
            email=normalized_email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            role=role,
        )
        session.add(user)
        session.flush()
        return user

    def get_by_id(self, session: Session, user_id: int):
        return session.get(self.user_model, user_id)

    def get_by_email(self, session: Session, email: str):
        normalized_email = email.lower().strip()
        statement = select(self.user_model).where(
            or_(
                self.user_model.normalized_email == normalized_email,
                self.user_model.email == normalized_email,
            )
        )
        return session.scalars(statement).first()
