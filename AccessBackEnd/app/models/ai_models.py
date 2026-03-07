from __future__ import annotations
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Integer, String, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base


class AIModel(Base):
    def __init__(self, **kw: Any):
        super().__init__(**kw)

    """Catalog of AI providers/models available to interactions."""

    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "model_id",
            name="uq_ai_models_provider_model_id"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    interactions: Mapped[list["AIInteraction"]] = relationship(back_populates="ai_model")
