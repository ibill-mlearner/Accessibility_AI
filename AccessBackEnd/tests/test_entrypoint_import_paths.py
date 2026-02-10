from __future__ import annotations

from importlib.machinery import PathFinder
from pathlib import Path


def test_backend_app_module_resolves_from_backend_directory() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "AccessBackEnd"

    spec = PathFinder.find_spec("app", [str(backend_dir)])

    assert spec is not None, "Expected to resolve backend-local 'app' package from AccessBackEnd/"


def test_backend_manage_uses_backend_local_imports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    manage_text = (repo_root / "AccessBackEnd" / "manage.py").read_text()

    assert "from app import create_app" in manage_text
    assert "from app.extensions import db" in manage_text
    assert "from AccessBackEnd.app import create_app" not in manage_text
