"""Audit logging ORM table.

Table map:
- `audit_logs`: immutable action trail with actor, action, target entity, and details payload.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    """Immutable audit records for sensitive application actions.

    Field map:
    - `id`: surrogate primary key for each audit event.
    - `actor_email`: indexed actor identifier for who performed the action.
    - `action`: verb/name describing the operation that occurred.
    - `entity_type`: logical entity name targeted by the operation.
    - `entity_id`: optional primary-key value of the targeted entity.
    - `details`: free-form details payload describing context and parameters.
    - `created_at`: timestamp when the audit record was captured.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_email: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
