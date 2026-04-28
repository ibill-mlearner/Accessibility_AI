from __future__ import annotations

from pathlib import Path

from app.db.settings import DatabaseSettings
from app.db.utilities import DatabaseSettingsUtilities


def test_resolve_database_url_defaults_to_backend_instance_dir(tmp_path):
    url = DatabaseSettings(instance_path=tmp_path.as_posix(), configured_url=None).resolve_database_url()

    assert url == f"sqlite:///{(tmp_path / 'accessibility_ai.db').resolve().as_posix()}"


def test_resolve_database_url_keeps_in_memory_sqlite_unchanged(tmp_path):
    url = DatabaseSettings(
        instance_path=tmp_path.as_posix(),
        configured_url='sqlite:///:memory:',
    ).resolve_database_url()

    assert url == 'sqlite:///:memory:'


def test_normalize_sqlite_url_resolves_relative_path_inside_instance_dir(tmp_path):
    url = DatabaseSettingsUtilities.normalize_sqlite_url(
        'sqlite:///data/nested.db',
        instance_path=tmp_path.as_posix(),
    )

    expected_path = (tmp_path / 'data' / 'nested.db').resolve().as_posix()
    assert url == f'sqlite:///{expected_path}'


def test_normalize_sqlite_url_leaves_non_sqlite_urls_unchanged(tmp_path):
    configured = 'postgresql://db.example.com/accessibility_ai'

    url = DatabaseSettingsUtilities.normalize_sqlite_url(configured, instance_path=tmp_path.as_posix())

    assert url == configured


def test_normalize_sqlite_url_handles_home_directory_expansion(tmp_path, monkeypatch):
    fake_home = tmp_path / 'home'
    monkeypatch.setenv('HOME', fake_home.as_posix())

    url = DatabaseSettingsUtilities.normalize_sqlite_url('sqlite:///~/app.db', instance_path=tmp_path.as_posix())

    expected_path = Path(fake_home / 'app.db').resolve().as_posix()
    assert url == f'sqlite:///{expected_path}'
