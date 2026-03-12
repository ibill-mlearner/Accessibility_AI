from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from .ai import AIInteraction, AIModel, AccommodationSystemPrompt, SystemPrompt
from .learning import Accommodation, UserAccessibilityFeature
from .audit_log import AuditLog
from .base import Base
from .learning import Chat, CourseClass, Message, Note, UserClassEnrollment
from .identity import Role, UserSession


class DBUser(Base):
    """Standalone DB user model used by app/db runtime and repositories."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    normalized_email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.STUDENT.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    email_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    lockout_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lockout_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    # Transitional placeholder until full identity policy enforcement is implemented.
    security_stamp: Mapped[str] = mapped_column(
        String(64), nullable=False, default=lambda: f"transitional-{hashlib.sha256('identity-placeholder'.encode('utf-8')).hexdigest()[:32]}"
    )

    chats: Mapped[list[Chat]] = relationship(back_populates="user", cascade="all, delete-orphan")
    taught_classes: Mapped[list[CourseClass]] = relationship(
        back_populates="instructor", foreign_keys=[CourseClass.instructor_id]
    )
    class_enrollments: Mapped[list[UserClassEnrollment]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    accessibility_features: Mapped[list[UserAccessibilityFeature]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @validates("email")
    def _set_normalized_email(self, _key: str, value: str) -> str:
        normalized = self._normalize_email(value)
        self.normalized_email = normalized
        return normalized

    def mark_login_success(self) -> None:
        self.last_login_at = datetime.now(timezone.utc)
        self.access_failed_count = 0


DB_MODELS = {
    "user": DBUser,
    "course_class": CourseClass,
    "chat": Chat,
    "message": Message,
    "note": Note,
    "user_class_enrollment": UserClassEnrollment,
    "ai_model": AIModel,
    "system_prompt": SystemPrompt,
    "accommodation_system_prompt": AccommodationSystemPrompt,
    "ai_interaction": AIInteraction,
    "accommodation": Accommodation,
    "user_accessibility_feature": UserAccessibilityFeature,
    "user_session": UserSession,
    "audit_log": AuditLog,
}


def get_schema_bundle() -> tuple[type[Base], dict[str, type[Base]]]:
    """Return the standalone DB base and app model map for app/db consumers."""

    return Base, DB_MODELS
