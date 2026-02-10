"""Logging and observer/event infrastructure.

Logging is deliberately decoupled from API handlers. Handlers publish domain events
that observers can subscribe to. The logging observer is attached in the app
factory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventObserver:
    def on_event(self, event: DomainEvent) -> None:  # pragma: no cover - protocol method
        raise NotImplementedError


class EventBus:
    def __init__(self) -> None:
        self._observers: list[EventObserver] = []

    def subscribe(self, observer: EventObserver) -> None:
        self._observers.append(observer)

    def publish(self, event: DomainEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)


class LoggingObserver(EventObserver):
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("app.events")

    def on_event(self, event: DomainEvent) -> None:
        self._logger.info("event=%s payload=%s occurred_at=%s", event.name, event.payload, event.occurred_at.isoformat())


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
