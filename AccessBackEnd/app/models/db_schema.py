from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Standalone SQLAlchemy declarative base used by the app/db package."""


class DBUser(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="student")

    chats: Mapped[list[Chat]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CourseClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="student")
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    chats: Mapped[list[Chat]] = relationship(back_populates="course_class", cascade="all, delete-orphan")
    notes: Mapped[list[Note]] = relationship(back_populates="course_class", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    course_class: Mapped[CourseClass] = relationship(back_populates="chats")
    user: Mapped[DBUser] = relationship(back_populates="chats")
    messages: Mapped[list[Message]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    notes: Mapped[list[Note]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    interactions: Mapped[list[AIInteraction]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    vote: Mapped[str] = mapped_column(String(16), nullable=False, default="good")
    note: Mapped[str] = mapped_column(String(8), nullable=False, default="no")
    help_intent: Mapped[str] = mapped_column(String(80), nullable=False)

    chat: Mapped[Chat] = relationship(back_populates="messages")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    noted_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    course_class: Mapped[CourseClass] = relationship(back_populates="notes")
    chat: Mapped[Chat] = relationship(back_populates="notes")


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id"), nullable=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    chat: Mapped[Chat | None] = relationship(back_populates="interactions")


DB_MODELS = {
    "user": DBUser,
    "course_class": CourseClass,
    "chat": Chat,
    "message": Message,
    "note": Note,
    "feature": Feature,
    "ai_interaction": AIInteraction,
}


def get_schema_bundle() -> tuple[type[Base], dict[str, type[Base]]]:
    """Return the standalone DB base and app model map for app/db consumers."""

    return Base, DB_MODELS
