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


def test_resolve_database_url_expands_relative_sqlite_path_into_instance_dir(tmp_path):
    url = resolve_database_url(
        instance_path=tmp_path.as_posix(),
        configured_url='sqlite:///data/test.db',
    )

    assert url == f"sqlite:///{(tmp_path / 'data' / 'test.db').resolve().as_posix()}"


def test_resolve_database_url_expands_environment_variable_in_sqlite_path(tmp_path, monkeypatch):
    monkeypatch.setenv('ACCESS_DB_FILE', 'env-db.sqlite3')
    url = resolve_database_url(
        instance_path=tmp_path.as_posix(),
        configured_url='sqlite:///$ACCESS_DB_FILE',
    )

    assert url == f"sqlite:///{(tmp_path / 'env-db.sqlite3').resolve().as_posix()}"


def test_resolve_database_url_uses_home_override_for_tilde_sqlite_path(tmp_path, monkeypatch):
    home_dir = tmp_path / 'custom-home'
    monkeypatch.setenv('HOME', home_dir.as_posix())

    url = resolve_database_url(
        instance_path=tmp_path.as_posix(),
        configured_url='sqlite:///~/tilde-db.sqlite',
    )

    assert url == f"sqlite:///{(home_dir / 'tilde-db.sqlite').resolve().as_posix()}"
