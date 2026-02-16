from __future__ import annotations

import json

from app import config as app_config
from app import create_app
from app.services.logging import InteractionLoggingService, RotatingTextLogWriter


class _FakeAIService:
    def run_interaction(self, prompt: str, context: dict | None = None) -> dict:
        return {"response_text": f"echo:{prompt}", "context": context or {}}


class _FailingAIService:
    def run_interaction(self, prompt: str, context: dict | None = None) -> dict:
        raise RuntimeError("upstream failure")


def test_interaction_logging_service_writes_user_and_context(tmp_path):
    writer = RotatingTextLogWriter(log_dir=tmp_path, max_lines=2000)
    service = InteractionLoggingService(wrapped=_FakeAIService(), writer=writer)

    result = service.run_interaction(
        "hello", context={"class_id": 12}, initiated_by="student_7"
    )

    assert result["response_text"] == "echo:hello"
    log_file = tmp_path / "ai_interactions_1.txt"
    assert log_file.exists()

    line = log_file.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["initiated_by"] == "student_7"
    assert payload["status"] == "success"
    assert payload["context"] == {"class_id": 12}


def test_interaction_logging_service_logs_failures_and_reraises(tmp_path):
    writer = RotatingTextLogWriter(log_dir=tmp_path, max_lines=2000)
    service = InteractionLoggingService(wrapped=_FailingAIService(), writer=writer)

    try:
        service.run_interaction("hello", initiated_by="student_8")
    except RuntimeError as exc:
        assert str(exc) == "upstream failure"
    else:
        raise AssertionError("RuntimeError expected")

    payload = json.loads(
        (tmp_path / "ai_interactions_1.txt").read_text(encoding="utf-8").strip()
    )
    assert payload["status"] == "failed"
    assert payload["initiated_by"] == "student_8"


def test_rotating_text_log_writer_rolls_after_max_lines(tmp_path):
    writer = RotatingTextLogWriter(log_dir=tmp_path, max_lines=2)

    writer.append("line-1")
    writer.append("line-2")
    writer.append("line-3")

    first = tmp_path / "ai_interactions_1.txt"
    second = tmp_path / "ai_interactions_2.txt"

    assert first.read_text(encoding="utf-8").splitlines() == ["line-1", "line-2"]
    assert second.read_text(encoding="utf-8").splitlines() == ["line-3"]


def test_ai_interaction_route_logs_to_configured_app_instance_dir(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        app_config.TestingConfig, "AI_INTERACTION_LOG_DIR", tmp_path.as_posix()
    )

    app = create_app("testing")
    ai_service = app.extensions["ai_service"]
    ai_service.run_interaction(
        "summarize", context={"chat_id": 4}, initiated_by="student_11"
    )

    log_path = tmp_path / "ai_interactions_1.txt"
    assert log_path.exists()

    payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["initiated_by"] == "student_11"
    assert payload["context"] == {"chat_id": 4}

    monkeypatch.setattr(app_config.TestingConfig, "AI_INTERACTION_LOG_DIR", None)


def test_ai_interaction_route_supports_deprecated_db_log_directory(
    monkeypatch, tmp_path, caplog
):
    monkeypatch.setattr(app_config.TestingConfig, "AI_INTERACTION_LOG_DIR", None)
    monkeypatch.setattr(
        app_config.TestingConfig, "DB_LOG_DIRECTORY", tmp_path.as_posix()
    )

    app = create_app("testing")
    ai_service = app.extensions["ai_service"]
    ai_service.run_interaction("legacy", context={"chat_id": 5}, initiated_by="student_12")

    assert (tmp_path / "ai_interactions_1.txt").exists()
    assert "DB_LOG_DIRECTORY is deprecated" in caplog.text

    monkeypatch.setattr(app_config.TestingConfig, "DB_LOG_DIRECTORY", None)
