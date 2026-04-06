from __future__ import annotations

import argparse

from app.db import init_flask_database
from app.extensions import db
from app.models import Accommodation
from app.utils.colorblind_accessibility_features_update import ensure_colorblind_accessibility_features
import manage as backend_manage


def test_ensure_colorblind_accessibility_features_adds_missing_rows(app):
    with app.app_context():
        init_flask_database(app)
        ensure_colorblind_accessibility_features(app)

        rows = (
            db.session.query(Accommodation)
            .filter(Accommodation.color_family.isnot(None))
            .order_by(Accommodation.color_family.asc())
            .all()
        )
        color_families = [row.color_family for row in rows]
        assert "protanopia-safe" in color_families
        assert "deuteranopia-safe" in color_families
        assert "tritanopia-safe" in color_families
        assert "achromatopsia-safe" in color_families
        assert all(row.displayable is True for row in rows if row.color_family in color_families)

        font_rows = (
            db.session.query(Accommodation)
            .filter(Accommodation.font_family.isnot(None))
            .order_by(Accommodation.font_family.asc())
            .all()
        )
        font_families = [row.font_family for row in font_rows]
        assert "opendyslexic" in font_families
        assert "atkinson" in font_families
        assert "arial" in font_families
        assert "verdana" in font_families
        assert "monospace" in font_families
        assert all(row.displayable is True for row in font_rows if row.font_family in font_families)


def test_ensure_colorblind_accessibility_features_updates_existing_deuteranopia_row(app):
    with app.app_context():
        init_flask_database(app)
        db.session.add(
            Accommodation(
                title="Color profile: Deuteranopia-safe palette",
                details="Old details",
                active=True,
                displayable=False,
                color_family="deuteranopia-safe",
            )
        )
        db.session.commit()

        ensure_colorblind_accessibility_features(app)

        rows = db.session.query(Accommodation).filter_by(color_family="deuteranopia-safe").all()
        assert len(rows) == 1
        row = rows[0]
        assert row.title == "Color family: Deuteranopia-safe"
        assert row.displayable is True
        assert "blue/orange" in row.details


def test_ensure_colorblind_accessibility_features_updates_existing_font_family_row(app):
    with app.app_context():
        init_flask_database(app)
        db.session.add(
            Accommodation(
                title="Font family: Open Dyslexic",
                details="Old details",
                active=True,
                displayable=False,
                font_family="opendyslexic",
            )
        )
        db.session.commit()

        ensure_colorblind_accessibility_features(app)

        rows = db.session.query(Accommodation).filter_by(font_family="opendyslexic").all()
        assert len(rows) == 1
        row = rows[0]
        assert row.title == "Font family: OpenDyslexic"
        assert row.displayable is True
        assert "dyslexia-friendly" in row.details


def test_build_runtime_app_calls_colorblind_feature_sync(monkeypatch):
    call_order: list[str] = []
    app = backend_manage.create_app("testing")

    def _apply_runtime_ai_overrides(_app, _args):
        call_order.append("apply_runtime_ai_overrides")

    def _run_init_db_flow(_app):
        call_order.append("run_init_db_flow")

    def _ensure_colorblind_features(_app):
        call_order.append("ensure_colorblind_accessibility_features")

    monkeypatch.setattr(backend_manage, "create_app", lambda _config: app)
    monkeypatch.setattr(backend_manage, "apply_runtime_ai_overrides", _apply_runtime_ai_overrides)
    monkeypatch.setattr(backend_manage, "run_init_db_flow", _run_init_db_flow)
    monkeypatch.setattr(
        backend_manage,
        "ensure_colorblind_accessibility_features",
        _ensure_colorblind_features,
    )

    args = argparse.Namespace(
        config="testing",
        ai_provider=None,
        ai_endpoint=None,
        host="0.0.0.0",
        port=5000,
        init_db=True,
        init_only=False,
    )
    runtime_app = backend_manage.build_runtime_app(args)

    assert runtime_app is app
    assert call_order == [
        "apply_runtime_ai_overrides",
        "run_init_db_flow",
        "ensure_colorblind_accessibility_features",
    ]
