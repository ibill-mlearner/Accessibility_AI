from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import configure_logging
from .events import EventBus, LoggingObserver
from .interaction_file_logger import InteractionLoggingService, RotatingTextLogWriter


DEFAULT_OBSERVER_TYPES = (LoggingObserver,)


def _ensure_default_observers(event_bus: EventBus) -> None:
    observers = getattr(event_bus, "_observers", [])
    for observer_type in DEFAULT_OBSERVER_TYPES:
        if not any(isinstance(observer, observer_type) for observer in observers):
            event_bus.subscribe(observer_type())


def initialize_logging(app: Flask) -> None:
    configure_logging(app.config["LOG_LEVEL"])

    event_bus = app.extensions.get("event_bus")
    if not isinstance(event_bus, EventBus):
        event_bus = EventBus()
        app.extensions["event_bus"] = event_bus

    _ensure_default_observers(event_bus)

    ai_service = app.extensions.get("ai_service")
    if ai_service is None or isinstance(ai_service, InteractionLoggingService):
        return

    interaction_log_dir = (
        app.config.get("AI_INTERACTION_LOG_DIR")
        or app.config.get("INTERACTION_LOG_DIR")
    )
    if not interaction_log_dir:
        interaction_log_dir = app.config.get("DB_LOG_DIRECTORY")
        if interaction_log_dir:
            app.logger.warning(
                "DB_LOG_DIRECTORY is deprecated; use AI_INTERACTION_LOG_DIR instead."
            )

    interaction_log_dir = interaction_log_dir or (
        Path(app.root_path) / "instance"
    ).as_posix()

    app.extensions["ai_service"] = InteractionLoggingService(
        wrapped=ai_service,
        writer=RotatingTextLogWriter(log_dir=Path(interaction_log_dir)),
    )
