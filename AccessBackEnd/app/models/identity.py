"""Identity/session ORM declarations.

Table map:
- `user_sessions`: persistent auth-session/token lifecycle records tied to `users`.
- `Role` enum values provide canonical authorization role names used across the app.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Role(StrEnum):
    """Canonical user roles for authorization and model defaults.

    Field map:
    - `STUDENT`: least-privileged learner role used for normal student accounts.
    - `INSTRUCTOR`: teaching role used for class/prompt ownership privileges.
    - `ADMIN`: elevated platform-administration role.
    """

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class UserSession(Base):
    """Persistent auth/session token state.

    Field map:
    - `id`: surrogate primary key for each session record.
    - `user_id`: required `users.id` reference for session ownership.
    - `token_hash`: unique one-way hash of the presented session token.
    - `created_at`: timestamp when the session row was first issued.
    - `expires_at`: timestamp when the session should expire.
    - `last_seen_at`: timestamp for the most recent authenticated usage.
    - `revoked_at`: timestamp indicating session revocation if invalidated early.
    - `user`: relationship handle to the owning `DBUser`.
    """

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    user: Mapped["DBUser"] = relationship(back_populates="sessions")
