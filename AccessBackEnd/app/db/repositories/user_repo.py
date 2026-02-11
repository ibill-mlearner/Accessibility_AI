from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    """Persistence helpers for standalone DB user records."""

    def __init__(self, user_model: type):
        self.user_model = user_model

    def create(self, session: Session, *, email: str, password_hash: str, role: str = "student"):
        user = self.user_model(email=email.lower().strip(), password_hash=password_hash, role=role)
        session.add(user)
        session.flush()
        return user

    def get_by_id(self, session: Session, user_id: int):
        return session.get(self.user_model, user_id)

    def get_by_email(self, session: Session, email: str):
        statement = select(self.user_model).where(self.user_model.email == email.lower().strip())
        return session.scalars(statement).first()
