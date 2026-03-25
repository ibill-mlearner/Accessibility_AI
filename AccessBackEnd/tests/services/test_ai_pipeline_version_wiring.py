from __future__ import annotations

from AccessBackEnd.app import create_app


def test_app_bootstrap_uses_ai_pipeline_thin_service(monkeypatch):
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    app = create_app("testing")

    service = app.extensions["ai_service"]
    wrapped = getattr(service, "_wrapped", service)
    assert wrapped.__class__.__module__ == "AccessBackEnd.app.services.ai_pipeline_thin_adapter"
