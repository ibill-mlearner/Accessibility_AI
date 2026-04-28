"""Core learning-domain ORM tables.

Table map:
- `accommodations`
- `user_accessibility_features`
- `classes`
- `user_class_enrollments`
- `chats`
- `messages`
- `notes`
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Accommodation(Base):
    """Global accommodation options reusable across classes/interactions.

    Field map:
    - `id`: surrogate primary key for each accommodation option.
    - `title`: unique display name shown in selection UIs.
    - `details`: longer explanation of what the accommodation does.
    - `active`: controls whether the option is generally available.
    - `displayable`: controls whether the option is visible in end-user surfaces.
    - `font_size_px`: optional constrained font-size hint for rendering adaptations.
    - `font_family`: optional font-family preference associated with this accommodation.
    - `color_family`: optional color palette/theme preference tied to this accommodation.
    - `prompt_links`: relationship collection to `AccommodationSystemPrompt` bridge rows.
    - `user_preferences`: relationship collection to per-user enablement rows.
    """

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
    font_family: Mapped[str | None] = mapped_column(String(80), nullable=True)
    color_family: Mapped[str | None] = mapped_column(String(80), nullable=True)

    prompt_links: Mapped[list["AccommodationSystemPrompt"]] = relationship(
        back_populates="accommodation", cascade="all, delete-orphan"
    )
    user_preferences: Mapped[list["UserAccessibilityFeature"]] = relationship(
        back_populates="accommodation", cascade="all, delete-orphan"
    )


class UserAccessibilityFeature(Base):
    """Per-user accessibility feature preference flags.

    Field map:
    - `id`: surrogate primary key for the preference record.
    - `user_id`: required `users.id` reference for the preference owner.
    - `accommodation_id`: required `accommodations.id` reference for the selected option.
    - `enabled`: boolean flag indicating whether this accommodation is active for the user.
    - `user`: relationship handle back to the owning `DBUser`.
    - `accommodation`: relationship handle back to the linked `Accommodation`.
    """

    __tablename__ = "user_accessibility_features"
    __table_args__ = (UniqueConstraint("user_id", "accommodation_id", name="uq_user_accessibility_feature"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["DBUser"] = relationship(back_populates="accessibility_features")
    accommodation: Mapped[Accommodation] = relationship(back_populates="user_preferences")


class CourseClass(Base):
    """Course context that groups chats and notes.

    Field map:
    - `id`: surrogate primary key for a class shell.
    - `name`: indexed class title used in listings and lookups.
    - `description`: class description text available to users/maintainers.
    - `instructor_id`: required `users.id` reference for the class owner.
    - `active`: boolean status indicating whether the class is currently active.
    - `instructor`: relationship handle to the teaching `DBUser`.
    - `enrollments`: relationship collection of `UserClassEnrollment` membership rows.
    - `chats`: relationship collection of class-bound conversation threads.
    - `notes`: relationship collection of notes associated with this class.
    """

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    # NOTE(ai-pipeline-thin): class descriptions are no longer injected into AI
    # system prompts; prompt composition is now based on guardrails + accessibility features.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # TODO: Decouple this single-owner link into a class-to-instructors association so one class can have many instructors.
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)

    instructor: Mapped["DBUser"] = relationship(back_populates="taught_classes")
    enrollments: Mapped[list["UserClassEnrollment"]] = relationship(
        back_populates="course_class", cascade="all, delete-orphan"
    )

    chats: Mapped[list["Chat"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")


class UserClassEnrollment(Base):
    """Many-to-many enrollment records between users and classes.

    Field map:
    - `id`: surrogate primary key for each enrollment row.
    - `user_id`: required `users.id` member reference.
    - `class_id`: required `classes.id` class reference.
    - `active`: enrollment-status flag for soft enable/disable behavior.
    - `user`: relationship handle to the enrolled `DBUser`.
    - `course_class`: relationship handle to the enrolled `CourseClass`.
    """

    __tablename__ = "user_class_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "class_id", name="uq_user_class_enrollment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped["DBUser"] = relationship(back_populates="class_enrollments")
    course_class: Mapped[CourseClass] = relationship(back_populates="enrollments")


class Chat(Base):
    """Conversation container owned by a user and optionally tied to a class.

    Field map:
    - `id`: surrogate primary key for each conversation.
    - `title`: user-facing title for the chat session.
    - `started_at`: timestamp for when the chat was created.
    - `model`: model label selected for the chat context.
    - `active`: soft-status flag for whether the chat is active/visible.
    - `class_id`: required `classes.id` reference for course context.
    - `user_id`: required `users.id` reference for chat ownership.
    - `ai_interaction_id`: optional pointer to the currently selected interaction.
    - `course_class`: relationship handle to the parent `CourseClass`.
    - `user`: relationship handle to the owning `DBUser`.
    - `messages`: relationship collection of `Message` rows in this chat.
    - `notes`: relationship collection of `Note` rows linked to this chat.
    - `interactions`: relationship collection of generated `AIInteraction` rows.
    - `selected_interaction`: relationship handle to the highlighted interaction row.
    """

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
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
    """Individual chat message and lightweight feedback metadata.

    Field map:
    - `id`: surrogate primary key for each message.
    - `chat_id`: required `chats.id` reference for conversation membership.
    - `message_text`: raw text body of the message content.
    - `vote`: coarse quality signal (for example good/bad) for user feedback.
    - `note`: compact marker indicating whether a note action occurred.
    - `help_intent`: internal label retained for backwards-compatible persistence defaults.
    - `chat`: relationship handle back to the owning `Chat`.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    vote: Mapped[str] = mapped_column(String(16), nullable=False, default="good")
    note: Mapped[str] = mapped_column(String(8), nullable=False, default="no")
    help_intent: Mapped[str] = mapped_column(String(80), nullable=False)

    chat: Mapped[Chat] = relationship(back_populates="messages")


class Note(Base):
    """Persistent class and chat note.

    Field map:
    - `id`: surrogate primary key for each note.
    - `class_id`: required `classes.id` reference for class association.
    - `chat_id`: required `chats.id` reference for conversation association.
    - `noted_on`: date the note should be considered authored/effective.
    - `content`: full note body text.
    - `course_class`: relationship handle to the linked `CourseClass`.
    - `chat`: relationship handle to the linked `Chat`.
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    noted_on: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    course_class: Mapped[CourseClass] = relationship(back_populates="notes")
    chat: Mapped[Chat] = relationship(back_populates="notes")
