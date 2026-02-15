from __future__ import annotations

import importlib.util
from pathlib import Path


MANAGE_PATH = Path(__file__).resolve().parents[1] / "manage.py"


def test_manage_import_has_no_cli_side_effects(monkeypatch):
    monkeypatch.setenv("APP_CONFIG", "testing")
    monkeypatch.setattr("sys.argv", ["manage.py", "--unknown-flag"])

    spec = importlib.util.spec_from_file_location("backend_manage_module", MANAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert module.app is not None
