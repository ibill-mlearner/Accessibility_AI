"""Logging services package surface.

Handoff note (high-level): this package owns application logging bootstrap, event-bus primitives,
and interaction-file logging wrappers used during AI request execution. Route and service code should
import logging primitives from this package surface rather than wiring logging internals ad hoc.
"""

from .bootstrap import initialize_logging
from .config import configure_logging
from .events import DomainEvent, EventBus, EventObserver, LoggingObserver
from .interaction_file_logger import (
    DEFAULT_LOG_BASENAME,
    MAX_LOG_LINES,
    InteractionLoggingService,
    RotatingTextLogWriter,
)
from .interfaces import (
    DomainEventInterface,
    EventBusInterface,
    EventObserverInterface,
    InteractionLoggingServiceInterface,
    InteractionLogWriterInterface,
    InteractionRunnerInterface,
)

__all__ = [
    "initialize_logging",
    "configure_logging",
    "DomainEvent",
    "EventBus",
    "EventObserver",
    "LoggingObserver",
    "DomainEventInterface",
    "EventBusInterface",
    "EventObserverInterface",
    "InteractionRunnerInterface",
    "InteractionLogWriterInterface",
    "InteractionLoggingServiceInterface",
    "DEFAULT_LOG_BASENAME",
    "MAX_LOG_LINES",
    "InteractionLoggingService",
    "RotatingTextLogWriter",
]
