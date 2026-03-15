from __future__ import annotations

from AccessBackEnd.app.db.configs import DBModuleConfig


def test_db_module_config_defaults(monkeypatch):
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    cfg = DBModuleConfig.from_env()
    assert cfg.sqlalchemy_database_uri is None
    assert cfg.migrations_dir == "migrations"
