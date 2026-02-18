"""Domain event primitives and observers."""

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

#todo: this is not actualy an Observer pattern right now
# need to debug further why, it is likely because the wrong package was used
# I was expecting flask.logging to be used which is an API observer
"""
Issue: Event bus logging is tightly coupled through API ingestion
this causes an overreliance on a single package that was built.

Solution: Register routes when app is stood up and not through the logging extension
Add actual system logging to file storage/db storage.
May be able to just switch the methods over to flask.logging and have pass through if else return with error handling
to avoid full refactor

"""
class EventObserver:
    def on_event(
        self, event: DomainEvent
    ) -> None:  # pragma: no cover - protocol method
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
        self._logger.info(
            "event=%s payload=%s occurred_at=%s",
            event.name,
            event.payload,
            event.occurred_at.isoformat(),
        )
