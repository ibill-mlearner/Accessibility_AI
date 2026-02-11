from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .accommodations import Accommodation
from .ai_interaction import AIInteraction, SystemPrompt
from .ai_models import AIModel, Feature
from .audit_log import AuditLog
from .base import Base
from .chats import Chat, CourseClass, Message, Note
from .role import Role
from .session import UserSession


class DBUser(Base):
    """Standalone DB user model used by app/db runtime and repositories."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.STUDENT.value)

    chats: Mapped[list[Chat]] = relationship(back_populates="user", cascade="all, delete-orphan")
    accommodations: Mapped[list[Accommodation]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete-orphan")


DB_MODELS = {
    "user": DBUser,
    "course_class": CourseClass,
    "chat": Chat,
    "message": Message,
    "note": Note,
    "feature": Feature,
    "ai_model": AIModel,
    "system_prompt": SystemPrompt,
    "ai_interaction": AIInteraction,
    "accommodation": Accommodation,
    "user_session": UserSession,
    "audit_log": AuditLog,
}


def get_schema_bundle() -> tuple[type[Base], dict[str, type[Base]]]:
    """Return the standalone DB base and app model map for app/db consumers."""

    return Base, DB_MODELS
