from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .role import Role


class CourseClass(Base):
    """Course context that groups chats and notes."""

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("name", "instructor_id", "term", name="uq_class_name_instructor_term"),
        UniqueConstraint("external_class_key", name="uq_class_external_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.STUDENT.value)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    term: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    section_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_class_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    instructor: Mapped["DBUser"] = relationship(back_populates="taught_classes")
    enrollments: Mapped[list["UserClassEnrollment"]] = relationship(
        back_populates="course_class", cascade="all, delete-orphan"
    )

    chats: Mapped[list["Chat"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")


class UserClassEnrollment(Base):
    """Many-to-many enrollment records between users and classes."""

    __tablename__ = "user_class_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "class_id", name="uq_user_class_enrollment"),
        CheckConstraint("role IN ('student', 'ta')", name="ck_user_class_enrollment_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=Role.STUDENT.value)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    course_class: Mapped[CourseClass] = relationship(back_populates="chats")
    user: Mapped["DBUser"] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    interactions: Mapped[list["AIInteraction"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


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
