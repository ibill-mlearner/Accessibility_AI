import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ARTIFACT_PATH = ROOT / "AccessBackEnd" / "tests" / "ai_test_analysis_log.txt"


def _append_artifact_line(message: str) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ARTIFACT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def pytest_sessionstart(session):
    _append_artifact_line(
        f"[{datetime.now(timezone.utc).isoformat()}] session_start cwd={os.getcwd()}"
    )


def pytest_runtest_logreport(report):
    if report.when == "call":
        _append_artifact_line(f"test={report.nodeid} outcome={report.outcome} duration_s={report.duration:.4f}")


def pytest_sessionfinish(session, exitstatus):
    _append_artifact_line(
        f"[{datetime.now(timezone.utc).isoformat()}] session_finish exitstatus={exitstatus}"
    )


@pytest.fixture()
def app():
    try:
        from AccessBackEnd.app import create_app
    except ModuleNotFoundError as exc:
        pytest.skip(f"app fixture unavailable due to missing dependency: {exc}")

    app = create_app("testing")
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
