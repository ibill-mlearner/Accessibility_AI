from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Accommodation(Base):
    """Global accommodation options reusable across classes/interactions."""

    __tablename__ = "accommodations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    prompt_links: Mapped[list["AccommodationSystemPrompt"]] = relationship(
        back_populates="accommodation", cascade="all, delete-orphan"
    )
