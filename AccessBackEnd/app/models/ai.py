"""AI-related ORM tables and relationships.

Table map:
- `ai_models`: catalog of provider/model ids available for runtime selection.
- `system_prompts`: instructor/class-scoped prompt text records.
- `accommodations_id_system_prompts`: join table linking accommodations to system prompts.
- `ai_interactions`: persisted AI request/response transcripts tied to chats/models/prompts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AIModel(Base):
    """Catalog of AI providers/models available to interactions.

    Field map:
    - `id`: surrogate primary key for internal references.
    - `provider`: upstream vendor name (for example, openai or anthropic).
    - `model_id`: provider-native model identifier used at inference time.
    - `source`: optional provenance label indicating where this model entry came from.
    - `path`: optional local/model-router path for self-hosted or proxied models.
    - `active`: feature flag for whether selection logic may use this model.
    - `created_at`: first persistence timestamp for the catalog record.
    - `updated_at`: last update timestamp for catalog metadata changes.
    - `interactions`: relationship collection of `AIInteraction` rows that used this model.
    """

    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint("provider", "model_id", name="uq_ai_models_provider_model_id"),
    )

    def __init__(self, **kw: Any):
        super().__init__(**kw)

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


class SystemPrompt(Base):
    """Class-scoped system prompts authored by instructors.

    Field map:
    - `id`: surrogate primary key for prompt references.
    - `instructor_id`: optional `users.id` owner for instructor-authored prompts.
    - `class_id`: optional `classes.id` scope that binds the prompt to a course.
    - `text`: full system prompt text injected into model calls.
    - `prompt_links`: relationship collection of accommodation-to-prompt bridge records.
    """

    __tablename__ = "system_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    prompt_links: Mapped[list["AccommodationSystemPrompt"]] = relationship(
        back_populates="system_prompt", cascade="all, delete-orphan"
    )


class AccommodationSystemPrompt(Base):
    """Combined accommodation + system prompt references for interaction prompting.

    Field map:
    - `id`: surrogate primary key for the bridge row.
    - `accommodation_id`: required `accommodations.id` reference for accessibility context.
    - `system_prompt_id`: required `system_prompts.id` reference for instruction context.
    - `accommodation`: relationship handle to the linked `Accommodation` row.
    - `system_prompt`: relationship handle to the linked `SystemPrompt` row.
    - `interactions`: relationship collection of `AIInteraction` rows using this pair.
    """

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
    """Provider-level request/response transcript tied to chat history.

    Field map:
    - `id`: surrogate primary key for each interaction event.
    - `chat_id`: optional `chats.id` back-reference for conversation grouping.
    - `accommodations_id_system_prompts_id`: optional bridge id that captures prompt+accommodation context.
    - `prompt`: final prompt text sent to the model provider.
    - `response_text`: model output text returned to the application.
    - `ai_model_id`: optional `ai_models.id` indicating the model used for generation.
    - `created_at`: timestamp of when the interaction was recorded.
    - `chat`: relationship handle back to the owning `Chat`.
    - `prompt_link`: relationship handle to the selected prompt/accommodation bridge row.
    - `ai_model`: relationship handle to the selected `AIModel`.
    """

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
