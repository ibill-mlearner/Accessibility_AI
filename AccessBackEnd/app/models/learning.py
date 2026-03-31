from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Accommodation(Base):
    """Global accommodation options reusable across classes/interactions."""

    __tablename__ = "accommodations"
    __table_args__ = (
        CheckConstraint(
            "font_size_px IS NULL OR font_size_px IN (14, 16, 18, 20, 24)",
            name="ck_accommodations_font_size_px",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    displayable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    font_size_px: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prompt_links: Mapped[list["AccommodationSystemPrompt"]] = relationship(
        back_populates="accommodation", cascade="all, delete-orphan"
    )
    user_preferences: Mapped[list["UserAccessibilityFeature"]] = relationship(
        back_populates="accommodation", cascade="all, delete-orphan"
    )


class UserAccessibilityFeature(Base):
    """Per-user accessibility feature preference flags."""

    __tablename__ = "user_accessibility_features"
    __table_args__ = (UniqueConstraint("user_id", "accommodation_id", name="uq_user_accessibility_feature"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["DBUser"] = relationship(back_populates="accessibility_features")
    accommodation: Mapped[Accommodation] = relationship(back_populates="user_preferences")


class CourseClass(Base):
    """Course context that groups chats and notes."""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    # NOTE(ai-pipeline-thin): class descriptions are no longer injected into AI
    # system prompts; prompt composition is now based on guardrails + accessibility features.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)

    instructor: Mapped["DBUser"] = relationship(back_populates="taught_classes")
    enrollments: Mapped[list["UserClassEnrollment"]] = relationship(
        back_populates="course_class", cascade="all, delete-orphan"
    )

    chats: Mapped[list["Chat"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")


class UserClassEnrollment(Base):
    """Many-to-many enrollment records between users and classes."""

    __tablename__ = "user_class_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "class_id", name="uq_user_class_enrollment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped["DBUser"] = relationship(back_populates="class_enrollments")
    course_class: Mapped[CourseClass] = relationship(back_populates="enrollments")


class Chat(Base):
    """Conversation container owned by a user and optionally tied to a class."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ai_interaction_id: Mapped[int | None] = mapped_column(ForeignKey("ai_interactions.id"), nullable=True, index=True)

    course_class: Mapped[CourseClass] = relationship(back_populates="chats")
    user: Mapped["DBUser"] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    interactions: Mapped[list["AIInteraction"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", foreign_keys="AIInteraction.chat_id"
    )
    selected_interaction: Mapped["AIInteraction | None"] = relationship(foreign_keys=[ai_interaction_id])


class Message(Base):
    """Individual chat message and lightweight feedback metadata."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    vote: Mapped[str] = mapped_column(String(16), nullable=False, default="good")
    note: Mapped[str] = mapped_column(String(8), nullable=False, default="no")
    help_intent: Mapped[str] = mapped_column(String(80), nullable=False)

    chat: Mapped[Chat] = relationship(back_populates="messages")


class Note(Base):
    """Persistent class and chat note."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    noted_on: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    course_class: Mapped[CourseClass] = relationship(back_populates="notes")
    chat: Mapped[Chat] = relationship(back_populates="notes")
