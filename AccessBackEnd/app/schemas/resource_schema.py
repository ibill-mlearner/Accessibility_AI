"""Chat/message payload contract placeholders for API v1 endpoints."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class ChatCreateRequest(TypedDict, total=False):
    """Placeholder payload for ``POST /api/v1/chats``."""

    class_id: int
    title: str
    model: str
    user_id: int


class ChatRecord(TypedDict, total=False):
    """Placeholder chat item returned in list/create responses."""

    id: int
    class_id: int
    user_id: int
    title: str
    model: str
    active: bool
    started_at: str


class ChatListResponse(TypedDict, total=False):
    """Placeholder response for ``GET /api/v1/chats``."""

    items: list[ChatRecord]
    next_cursor: str | None


class MessageCreateRequest(TypedDict, total=False):
    """Placeholder payload for ``POST /api/v1/chats/<chat_id>/messages``."""

    message_text: str
    role: Literal["user", "assistant", "system"]
    vote: Literal["good", "bad"]
    note: Literal["yes", "no"]
    help_intent: str
    metadata: dict[str, Any]


class MessageRecord(TypedDict, total=False):
    """Placeholder message item returned in list/create responses."""

    id: int
    chat_id: int
    role: str
    message_text: str
    vote: Literal["good", "bad"]
    note: Literal["yes", "no"]
    help_intent: str
    created_at: str
    metadata: dict[str, Any]


class MessageListResponse(TypedDict, total=False):
    """Placeholder response for ``GET /api/v1/chats/<chat_id>/messages``."""

    chat_id: int
    items: list[MessageRecord]
    next_cursor: str | None


class PlaceholderTodoResponse(TypedDict, total=False):
    """Explicit TODO response contract returned by stub handlers."""

    message: str
    endpoint: str
    next_steps: list[str]
    payload: dict[str, Any]
