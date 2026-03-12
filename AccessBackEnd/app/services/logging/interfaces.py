from __future__ import annotations

"""Contracts for the logging service module.

This module defines the stable interfaces consumed by application bootstrapping and
feature modules. The goal is to keep callers coupled to behavior contracts instead
of concrete files/classes so implementations can change with minimal ripple effects.

Behavior expectations:
- Event bus implementations keep observer registration order and publish events to
  every subscribed observer.
- Observer implementations should not raise for normal event payloads.
- Interaction logging wrappers must be transparent to callers: they delegate to the
  wrapped service and preserve the wrapped return value/exception behavior.
- Log writers are append-only sinks and are expected to handle their own I/O
  synchronization strategy.
"""

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from ..ai_pipeline_v2.types import AIPipelineRequest


@runtime_checkable
class DomainEventInterface(Protocol):
    """Structured event emitted by domain modules."""

    name: str
    payload: dict[str, Any]
    occurred_at: datetime


@runtime_checkable
class EventObserverInterface(Protocol):
    """Observer that receives published domain events."""

    def on_event(self, event: DomainEventInterface) -> None:
        ...


@runtime_checkable
class EventBusInterface(Protocol):
    """Publish/subscribe event dispatcher."""

    def subscribe(self, observer: EventObserverInterface) -> None:
        ...

    def publish(self, event: DomainEventInterface) -> None:
        ...


@runtime_checkable
class InteractionRunnerInterface(Protocol):
    """Underlying AI interaction service contract."""

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        ...

    def run_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...


@runtime_checkable
class InteractionLogWriterInterface(Protocol):
    """Append-only sink used by interaction logging wrappers."""

    def append(self, line: str) -> None:
        ...


@runtime_checkable
class InteractionLoggingServiceInterface(InteractionRunnerInterface, Protocol):
    """Decorator service that logs interaction metadata and delegates execution."""

    is_interaction_logging_wrapper: bool
