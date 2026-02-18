from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SystemPrompt(Base):
    """Class-scoped system prompts authored by instructors."""

    __tablename__ = "system_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    prompt_links: Mapped[list["AccommodationSystemPrompt"]] = relationship(
        back_populates="system_prompt", cascade="all, delete-orphan"
    )


class AccommodationSystemPrompt(Base):
    """Combined accommodation + system prompt references for interaction prompting."""

    __tablename__ = "accommodations_id_system_prompts"
    __table_args__ = (
        UniqueConstraint("accommodation_id", "system_prompt_id", name="uq_accommodation_system_prompt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id"), nullable=False, index=True)
    system_prompt_id: Mapped[int] = mapped_column(ForeignKey("system_prompts.id"), nullable=False, index=True)

    accommodation: Mapped["Accommodation"] = relationship(back_populates="prompt_links")
    system_prompt: Mapped["SystemPrompt"] = relationship(back_populates="prompt_links")
    interactions: Mapped[list["AIInteraction"]] = relationship(back_populates="prompt_link")


class AIInteraction(Base):
    """Provider-level request/response transcript tied to chat history."""

    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id"), nullable=True, index=True)
    accommodations_id_system_prompts_id: Mapped[int | None] = mapped_column(
        ForeignKey("accommodations_id_system_prompts.id"), nullable=True, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_model_id: Mapped[int | None] = mapped_column(ForeignKey("ai_models.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    chat: Mapped["Chat"] = relationship(back_populates="interactions", foreign_keys=[chat_id])
    prompt_link: Mapped["AccommodationSystemPrompt | None"] = relationship(back_populates="interactions")
    ai_model: Mapped["AIModel | None"] = relationship(back_populates="interactions")
