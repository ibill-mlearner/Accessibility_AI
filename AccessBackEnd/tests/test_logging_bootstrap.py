from __future__ import annotations

from pathlib import Path

from flask import Flask

from ..app.services.logging import bootstrap


class _FakeThread:
    def __init__(self, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True


class _FakeProcess:
    def __init__(self, lines: list[str], exit_code: int):
        self.stdout = iter(lines)
        self._exit_code = exit_code

    def wait(self) -> int:
        return self._exit_code


def _build_app(**config) -> Flask:
    app = Flask(__name__)
    app.config.update(
        STARTUP_TEST_RUNNER_ENABLED=False,
        STARTUP_TEST_RUNNER_COMMAND="python -m pytest tests -q",
        STARTUP_TEST_RUNNER_CWD=None,
        LOG_LEVEL="INFO",
    )
    app.config.update(config)
    return app


def test_startup_test_runner_starts_background_thread(monkeypatch):
    app = _build_app(STARTUP_TEST_RUNNER_ENABLED=True)

    started_threads = []

    def _fake_thread(*, target, name, daemon):
        thread = _FakeThread(target=target, name=name, daemon=daemon)
        started_threads.append(thread)
        return thread

    monkeypatch.setattr(bootstrap.threading, "Thread", _fake_thread)

    bootstrap._start_startup_test_runner(app)

    assert app.extensions["startup_test_runner_started"] is True
    assert len(started_threads) == 1
    assert started_threads[0].name == "startup-test-runner"
    assert started_threads[0].daemon is True
    assert started_threads[0].started is True


def test_startup_test_runner_logs_output_and_exit_code(monkeypatch):
    app = _build_app()

    log_messages: list[tuple[str, str]] = []
    monkeypatch.setattr(app.logger, "info", lambda message, *args: log_messages.append(("info", message % args)))
    monkeypatch.setattr(app.logger, "warning", lambda message, *args: log_messages.append(("warning", message % args)))

    def _fake_popen(*args, **kwargs):
        return _FakeProcess(lines=["collected 2 items\n", "2 passed\n"], exit_code=0)

    monkeypatch.setattr(bootstrap.subprocess, "Popen", _fake_popen)

    bootstrap._run_startup_tests(app, command="python -m pytest tests -q", cwd=Path("."))

    assert ("info", "startup_test_runner.start command=python -m pytest tests -q cwd=.") in log_messages
    assert ("info", "startup_test_runner.output collected 2 items") in log_messages
    assert ("info", "startup_test_runner.output 2 passed") in log_messages
    assert ("info", "startup_test_runner.finish exit_code=0") in log_messages
