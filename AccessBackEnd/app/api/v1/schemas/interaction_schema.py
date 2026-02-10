"""Interaction request/response shape definitions for the v1 API.

These are intentionally lightweight contracts that describe payload intent.
No transformation or coercion should happen here.
"""

from __future__ import annotations

from typing import Any, TypedDict


class RetrievalContext(TypedDict, total=False):
    """Placeholder contract for future Retrieval-Augmented Generation inputs."""

    source: str
    query: str
    documents: list[dict[str, Any]]


class AIInteractionRequest(TypedDict, total=False):
    """Payload accepted by ``POST /api/v1/ai/interactions``.

    Logic intent:
    - Accept prompt/context values as submitted by the client.
    - Leave room for upcoming system prompts and RAG context.
    - Pass the currently supported prompt field directly to AI service.
    """

    prompt: str
    system_prompt: str
    context: dict[str, Any]
    rag: RetrievalContext
    conversation_id: str


class AIInteractionResponse(TypedDict, total=False):
    """Pass-through response returned from the AI service."""

    data: Any
    error: str
    meta: dict[str, Any]
