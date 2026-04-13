from __future__ import annotations

from pathlib import Path
from importlib import util
from flask import Flask

from ...api.v1.routes import db
from ...models import AIModel
from .validators import AIInteractionValidator


def _discover_model_ids(models_root: Path) -> list[str]:
    if not models_root.exists() or not models_root.is_dir():
        return []
    return sorted(child.name for child in models_root.iterdir() if child.is_dir())


def _resolve_local_models_root(app: Flask) -> Path:
    project_root = Path(app.root_path).resolve().parents[1]
    # Model inventory lookup order:
    # 1) Legacy thin runtime folder under the repo (if present).
    # 2) Installed ai_pipeline package models cache directory (if present).
    # 3) <app.instance_path>/models fallback.
    thin_models_root = project_root / "app" / "services" / "ai_pipeline_thin" / "models"
    if thin_models_root.exists() and thin_models_root.is_dir():
        return thin_models_root

    installed_models_root = _resolve_installed_pipeline_models_root()
    if installed_models_root is not None:
        return installed_models_root

    return Path(app.instance_path) / "models"


def _resolve_installed_pipeline_models_root() -> Path | None:
    spec = util.find_spec("ai_pipeline.model_loader")
    if spec is None or not spec.origin:
        return None

    models_root = Path(spec.origin).resolve().parent / "models"
    if not models_root.exists() or not models_root.is_dir():
        return None
    return models_root


def sync_ai_models_with_local_inventory(app: Flask) -> dict[str, int | str | None]:
    provider = AIInteractionValidator.to_clean_text(app.config.get("AI_PROVIDER"), lower=True) or "huggingface"
    models_root = _resolve_local_models_root(app)
    discovered_model_ids = _discover_model_ids(models_root)
    default_model_id = str(app.config.get("AI_MODEL_NAME") or "").strip()

    records = db.session.query(AIModel).filter(AIModel.provider == provider).all()
    by_model_id = {record.model_id: record for record in records}
    discovered_set = set(discovered_model_ids)

    upserted = 0
    for model_id in discovered_model_ids:
        path = (models_root / model_id).as_posix()
        record = by_model_id.get(model_id)
        is_default = bool(default_model_id and model_id == default_model_id)
        if record is None:
            db.session.add(AIModel(provider=provider, model_id=model_id, source="instance_models", path=path, active=is_default))
            upserted += 1
            continue
        record.source = "instance_models"
        record.path = path
        record.active = is_default
        upserted += 1

    marked_inactive = 0
    for record in records:
        if record.model_id in discovered_set:
            continue
        if record.active:
            marked_inactive += 1
        record.active = False

    # NOTE(step-1 analysis): `by_model_id` is built before discovered inserts above.
    # If `default_model_id` matches a newly discovered directory and there was no
    # pre-existing row, this branch can attempt a duplicate insert. Keep this
    # behavior unchanged for now; we are documenting workflow/edge cases first.
    if default_model_id and default_model_id not in by_model_id:
        default_path = (models_root / default_model_id).as_posix()
        db.session.add(AIModel(provider=provider, model_id=default_model_id, source="config_default", path=default_path, active=True))
        upserted += 1

    db.session.commit()
    return {
        "provider": provider,
        "discovered": len(discovered_model_ids),
        "upserted": upserted,
        "marked_inactive": marked_inactive,
        "default_model_id": default_model_id or None,
    }


__all__ = ["sync_ai_models_with_local_inventory"]
