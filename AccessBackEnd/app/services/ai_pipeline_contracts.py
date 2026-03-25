from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class AIPipelineRequest:
    prompt: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    chat_id: int | None = None
    initiated_by: str | None = None
    class_id: int | None = None
    user_id: int | None = None


class AIPipelineUpstreamError(RuntimeError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


@runtime_checkable
class AIPipelineServiceInterface(Protocol):
    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        ...

    def run_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    def list_available_models(self) -> dict[str, Any]:
        ...
