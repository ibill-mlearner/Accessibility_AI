from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class AIPipelineRequest:
    prompt: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    chat_id: int | None = None
    initiated_by: str | None = None
    class_id: int | None = None
    user_id: int | str | None = None
    rag: dict[str, Any] | None = None


@dataclass(slots=True)
class AIPipelineUpstreamError(RuntimeError):
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)


class AIPipelineServiceInterface(Protocol):
    def run(self, request: AIPipelineRequest) -> dict[str, Any]: ...
    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **metadata: Any) -> dict[str, Any]: ...
    def generate_text(self, text: str, model_name: str) -> dict[str, Any]: ...
    def provider_health(self) -> dict[str, Any]: ...
    def list_available_models(self) -> dict[str, Any]: ...
