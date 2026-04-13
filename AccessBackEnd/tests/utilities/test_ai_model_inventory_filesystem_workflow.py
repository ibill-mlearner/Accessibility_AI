from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


def test_resolve_local_models_root_falls_back_to_instance_models_when_thin_dir_missing(tmp_path):
    from app.utils.ai_checker.operations import _resolve_local_models_root

    project_root = tmp_path / "project"
    root_path = project_root / "AccessBackEnd" / "app"
    instance_path = project_root / "AccessBackEnd" / "instance"
    root_path.mkdir(parents=True)
    instance_path.mkdir(parents=True)

    fake_app = SimpleNamespace(root_path=str(root_path), instance_path=str(instance_path))

    resolved = _resolve_local_models_root(fake_app)

    assert resolved == instance_path / "models"


def test_sync_ai_models_with_local_inventory_reads_filesystem_and_writes_db(app, tmp_path, monkeypatch):
    from app.db import init_flask_database
    from app.extensions import db
    from app.models import AIModel
    from app.utils.ai_checker import operations as ai_operations

    models_root = tmp_path / "models"
    (models_root / "HuggingFaceTB--SmolLM2-360M-Instruct").mkdir(parents=True)
    (models_root / "Qwen--Qwen2.5-0.5B-Instruct").mkdir(parents=True)

    with app.app_context():
        init_flask_database(app)
        app.config["AI_PROVIDER"] = "huggingface"
        # Use a config default value that is not one of the discovered directory names
        # so we can verify both inventory-discovered rows and config_default row behavior.
        app.config["AI_MODEL_NAME"] = "virtual/models/default-runtime-pointer"

        monkeypatch.setattr(ai_operations, "_resolve_local_models_root", lambda _: models_root)

        payload = ai_operations.sync_ai_models_with_local_inventory(app)

        rows = (
            db.session.query(AIModel)
            .filter(AIModel.provider == "huggingface")
            .order_by(AIModel.model_id.asc())
            .all()
        )

    assert payload["discovered"] == 2
    assert payload["upserted"] == 3
    assert payload["provider"] == "huggingface"
    assert [row.model_id for row in rows] == [
        "HuggingFaceTB--SmolLM2-360M-Instruct",
        "Qwen--Qwen2.5-0.5B-Instruct",
        "virtual/models/default-runtime-pointer",
    ]
    assert [row.path for row in rows] == [
        (models_root / "HuggingFaceTB--SmolLM2-360M-Instruct").as_posix(),
        (models_root / "Qwen--Qwen2.5-0.5B-Instruct").as_posix(),
        (models_root / "virtual/models/default-runtime-pointer").as_posix(),
    ]
    assert [row.active for row in rows] == [False, False, True]


@pytest.mark.xfail(reason="Known inventory-sync edge case: discovered default model can be inserted twice.", strict=True)
def test_sync_ai_models_with_local_inventory_duplicate_insert_when_default_is_discovered(app, tmp_path, monkeypatch):
    from app.db import init_flask_database
    from app.utils.ai_checker import operations as ai_operations

    models_root = tmp_path / "models"
    (models_root / "Qwen--Qwen2.5-0.5B-Instruct").mkdir(parents=True)

    with app.app_context():
        init_flask_database(app)
        app.config["AI_PROVIDER"] = "huggingface"
        app.config["AI_MODEL_NAME"] = "Qwen--Qwen2.5-0.5B-Instruct"
        monkeypatch.setattr(ai_operations, "_resolve_local_models_root", lambda _: models_root)
        ai_operations.sync_ai_models_with_local_inventory(app)
