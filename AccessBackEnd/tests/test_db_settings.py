from __future__ import annotations

from pathlib import Path

from app.db.settings import resolve_database_url


def test_resolve_database_url_defaults_to_backend_instance_dir(tmp_path):
    url = resolve_database_url(instance_path=tmp_path.as_posix(), configured_url=None)

    assert url == f"sqlite:///{(tmp_path / 'accessibility_ai.db').resolve().as_posix()}"


def test_resolve_database_url_normalizes_relative_sqlite_driver_variants(tmp_path):
    configured = "sqlite+pysqlite:///runtime/dev.sqlite3"

    url = resolve_database_url(instance_path=tmp_path.as_posix(), configured_url=configured)

    expected_file = (tmp_path / "runtime" / "dev.sqlite3").resolve()
    assert url == f"sqlite+pysqlite:///{expected_file.as_posix()}"
    assert expected_file.parent.exists()


def test_resolve_database_url_preserves_absolute_sqlite_paths(tmp_path):
    absolute_file = (tmp_path / "absolute.sqlite3").resolve()
    configured = f"sqlite:///{absolute_file.as_posix()}"

    url = resolve_database_url(instance_path=(tmp_path / "ignored").as_posix(), configured_url=configured)

    assert url == configured
