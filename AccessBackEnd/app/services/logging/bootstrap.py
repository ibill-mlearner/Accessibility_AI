from __future__ import annotations

from pathlib import Path

from flask import Flask
# tests don't have the same threading that Flask ans WSGI are built in with
import os
import shlex
import subprocess
import threading

from .config import configure_logging
from .events import EventBus, LoggingObserver
from .interaction_file_logger import InteractionLoggingService, RotatingTextLogWriter
from .interfaces import EventBusInterface


DEFAULT_OBSERVER_TYPES = (LoggingObserver,)

"""
Bootstrap guidance:
- For standard request/application logs, prefer Flask's built-in logging setup.
- This module's EventBus + LoggingObserver path is for domain-event fan-out where multiple
  consumers may react to the same event.
- If you do not need fan-out semantics, direct Flask logger usage is typically the leaner path.
"""


# Handoff note: ensure at least one default observer exists so published events are not silently dropped.
def _ensure_default_observers(event_bus: EventBusInterface) -> None:
    observers = getattr(event_bus, "_observers", [])
    for observer_type in DEFAULT_OBSERVER_TYPES:
        if not any(isinstance(observer, observer_type) for observer in observers):
            event_bus.subscribe(observer_type())


# Handoff note: normalize startup test command into a readable log-string form.
def _render_startup_command(command: str | list[str]) -> str:
    return command if isinstance(command, str) else " ".join(command)


# Handoff note: normalize startup test command into argv for subprocess execution.
def _startup_command_argv(command: str | list[str]) -> list[str]:
    return shlex.split(command) if isinstance(command, str) else list(command)


# Handoff note: run optional startup smoke tests and stream output into app logger.
def _run_startup_tests(app: Flask, command: str | list[str], cwd: Path) -> None:
    app.logger.info("startup_test_runner.start command=%s cwd=%s", _render_startup_command(command), cwd)

    argv = _startup_command_argv(command)
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert process.stdout is not None
    for line in process.stdout:
        app.logger.info("startup_test_runner.output %s", line.rstrip())

    exit_code = process.wait()
    level = app.logger.info if exit_code == 0 else app.logger.warning
    level("startup_test_runner.finish exit_code=%s", exit_code)


# Handoff note: gate and launch optional startup-test runner in background thread during app bootstrap
# (primarily useful for dev/handoff verification; can remain disabled in production profiles).
def _start_startup_test_runner(app: Flask) -> None:
    if not app.config.get("STARTUP_TEST_RUNNER_ENABLED", False):
        return

    if app.extensions.get("startup_test_runner_started"):
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        app.logger.debug("startup_test_runner.skip reason=debug_reloader_parent")
        return

    command = app.config.get("STARTUP_TEST_RUNNER_COMMAND")
    if not command:
        app.logger.warning("startup_test_runner.skip reason=missing_command")
        return

    cwd = Path(app.config.get("STARTUP_TEST_RUNNER_CWD") or Path(__file__).resolve().parents[3])

    def _runner() -> None:
        try:
            _run_startup_tests(app, command=command, cwd=cwd)
        except Exception:
            app.logger.exception("startup_test_runner.error")

    app.extensions["startup_test_runner_started"] = True
    threading.Thread(target=_runner, name="startup-test-runner", daemon=True).start()

# Handoff note: primary logging bootstrap that wires log config, event bus observers, and interaction log wrapper.
def initialize_logging(app: Flask) -> None:
    configure_logging(app.config["LOG_LEVEL"])
    _start_startup_test_runner(app)

    event_bus = app.extensions.get("event_bus")
    if not isinstance(event_bus, EventBus):
        event_bus = EventBus()
        app.extensions["event_bus"] = event_bus

    _ensure_default_observers(event_bus)

    ai_service = app.extensions.get("ai_service")
    if ai_service is None or getattr(ai_service, "is_interaction_logging_wrapper", False):
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

    interaction_log_dir = interaction_log_dir or Path(app.instance_path).as_posix()

    app.extensions["ai_service"] = InteractionLoggingService(
        wrapped=ai_service,
        writer=RotatingTextLogWriter(log_dir=Path(interaction_log_dir)),
    )
