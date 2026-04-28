from __future__ import annotations

from app.db.settings import DatabaseSettings


def test_resolve_database_url_defaults_to_backend_instance_dir(tmp_path):
    url = DatabaseSettings(instance_path=tmp_path.as_posix(), configured_url=None).resolve_database_url()

    assert url == f"sqlite:///{(tmp_path / 'accessibility_ai.db').resolve().as_posix()}"


def test_resolve_database_url_keeps_in_memory_sqlite_unchanged(tmp_path):
    url = DatabaseSettings(
        instance_path=tmp_path.as_posix(),
        configured_url='sqlite:///:memory:',
    ).resolve_database_url()

    assert url == 'sqlite:///:memory:'
