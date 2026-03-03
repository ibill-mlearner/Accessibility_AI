from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PipelineRequest:
    """Input payload for the AI pipeline.

    # Logic intent:
    # - Normalize request shape for pipeline stages and provider calls.
    # - Allow contextual metadata that can be logged/audited alongside prompt content.
    """

    prompt: str
    context: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class AIPipelineRequest:
    """Stable API-layer request DTO for AI pipeline execution."""

    messages: list[dict] = field(default_factory=list)
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    # Optional request metadata
    chat_id: int | None = None
    initiated_by: str | None = None
    class_id: int | None = None
    user_id: int | str | None = None
    rag: dict[str, Any] | None = None
    request_id: str | None = None
    
@dataclass(slots=True)
class PipelineResponse:
    """Output payload returned from the AI pipeline.

    # Logic intent:
    # - Enforce JSON-compatible dictionary output for API consumers.
    # - Attach metadata describing provider, model, and execution stages.
    """

    data: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)
