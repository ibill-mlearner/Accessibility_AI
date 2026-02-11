"""Resource payload shapes for API v1 pass-through endpoints."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

# ``class`` uses functional TypedDict form to avoid keyword collision.
ChatRecord = TypedDict(
    "ChatRecord",
    {
        "id": int,
        "title": str,
        "start": str,
        "model": str,
        "class": str,
        "user": str,
    },
    total=False,
)


class MessageRecord(TypedDict, total=False):
    """Pass-through message record contract.

    Logic intent:
    - Keep message data in a separate collection from chats.
    - Preserve metadata flags for future analytics and intent workflows.
    """

    id: int
    chat_id: int
    message_text: str
    vote: Literal["good", "bad"]
    note: Literal["yes", "no"]
    help_intent: str


class ResourceRecord(TypedDict, total=False):
    """Generic record fallback for resources with non-finalized structure."""

    id: int | str


class ResourceEnvelope(TypedDict):
    """Simple list response wrapper."""

    items: list[dict[str, Any]]
