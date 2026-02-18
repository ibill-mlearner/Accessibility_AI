from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AIModel(Base):
    """Catalog of AI providers/models available to interactions."""

    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    interactions: Mapped[list["AIInteraction"]] = relationship(back_populates="ai_model")
