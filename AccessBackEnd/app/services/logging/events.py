"""Domain event primitives and observers.

Current design is an in-process synchronous event bus intended for lightweight app telemetry.
`default_factory` below is the dataclasses standard argument name (not a project-local variable);
it provides per-instance defaults for mutable fields and timestamps.

Celery note (can/should, not force): Celery can be a better fit if durable queues, retries,
or cross-process worker distribution become requirements. For current handoff scope, the
in-process bus remains simpler and sufficient unless those requirements are explicitly adopted.

Maintenance note:
- `EventObserver.on_event()` raises `NotImplementedError` intentionally as a base-class contract,
  not as an unfinished TODO. Concrete observers (like `LoggingObserver`) must implement it.
- If only plain request/app logs are needed, Flask's native logging stack is usually enough and
  this pub/sub layer may be more complexity than required.
- Keep this EventBus path for explicit domain-event fan-out; otherwise prefer direct Flask logging.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .interfaces import DomainEventInterface, EventBusInterface, EventObserverInterface


@dataclass(slots=True)
# Handoff note: event envelope carrying name/payload/timestamp; dataclass `default_factory`
# is used so each instance gets its own payload dict and current UTC timestamp.
class DomainEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

# Handoff note: observer base contract for handling domain events published through EventBus.
class EventObserver(EventObserverInterface):
    # Handoff note: override point for concrete observer handlers.
    # NotImplementedError here is intentional: fail fast if a base observer is used directly.
    def on_event(
        self, event: DomainEvent
    ) -> None:  # pragma: no cover - protocol method
        raise NotImplementedError


# Handoff note: in-process synchronous pub/sub bus used by API/service event emitters.
class EventBus(EventBusInterface):
    # Handoff note: maintain observer registration list for this process instance.
    def __init__(self) -> None:
        self._observers: list[EventObserver] = []

    # Handoff note: register observers in-order; publish dispatches in this same order.
    def subscribe(self, observer: EventObserver) -> None:
        self._observers.append(observer)

    # Handoff note: synchronously fan out events to all registered observers in-process
    # (no queue/retry semantics; evaluate Celery only if durability/retry requirements emerge).
    def publish(self, event: DomainEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)


# Handoff note: default observer that writes published events into structured logger output.
class LoggingObserver(EventObserver):
    # Handoff note: allow logger injection for tests/custom routing; fallback to app.events logger.
    # Prefer this observer for domain events instead of sprinkling manual print/debug statements.
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("app.events")

    # Handoff note: emit compact structured event line containing name, payload, and timestamp.
    def on_event(self, event: DomainEvent) -> None:
        self._logger.info(
            "event=%s payload=%s occurred_at=%s",
            event.name,
            event.payload,
            event.occurred_at.isoformat(),
        )
