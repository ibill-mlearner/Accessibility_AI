"""Typed interaction request/response shape definitions for API v1.

These TypedDict contracts document expected interaction payload envelopes and response fields for
editor/autocomplete/readability purposes. Runtime acceptance rules still come from Marshmallow
schemas and route validation; this file documents intent and stable consumer-facing structure.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ChatMessage(TypedDict):
    """Backwards-compatible chat message for AI interaction request payloads."""

    role: str
    content: str


class AIInteractionRequest(TypedDict, total=False):
    """Payload accepted by ``POST /api/v1/ai/interactions``.

    Logic intent:
    - Accept prompt/context values as submitted by the client.
    - Leave room for upcoming system prompts.
    - Pass the currently supported prompt field directly to AI service.
    """

    prompt: str
    system_prompt: str
    context: dict[str, Any]
    conversation_id: str
    chat_id: int
    messages: list[ChatMessage]


class AIInteractionResponse(TypedDict):
    """Canonical response shape consumed by UI clients."""

    # Logic intent:
    # - Keep user-visible output in a single stable text field.
    # - Preserve optional scoring and notes for incremental UX improvements.
    # - Reserve provider-specific details for metadata/debug rendering.
    assistant_text: str
    confidence: float | None
    notes: list[str]
    meta: dict[str, Any]
