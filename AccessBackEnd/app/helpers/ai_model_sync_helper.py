from __future__ import annotations

from pathlib import Path

from flask import Flask

from ..extensions import db
from ..models import AIModel
from ..services.ai_pipeline.providers import normalize_provider_name


def _discover_model_ids(
        models_root: Path
    ) -> list[str]:
    if not models_root.exists() or not models_root.is_dir():
        return []
    return sorted(child.name for child in models_root.iterdir() if child.is_dir())


def _index_records_by_model_id(
        records: list[AIModel]
    ) -> dict[str, AIModel]:
    return {record.model_id: record for record in records}


def _upsert_discovered_models(
    *,
    provider: str,
    models_root: Path,
    discovered_model_ids: list[str],
    by_model_id: dict[str, AIModel],
    default_model_id: str,
    ) -> int:
    counter = 0
    for model_id in discovered_model_ids:
        record = by_model_id.get(model_id)
        model_path = (models_root / model_id).resolve().as_posix()
        is_default = bool(default_model_id and model_id == default_model_id)
        if record is None:
            db.session.add(
                AIModel(
                    provider=provider,
                    model_id=model_id,
                    source="instance_models",
                    path=model_path,
                    active=is_default,
                )
            )
            counter += 1
            continue

        record.source = "instance_models"
        record.path = model_path
        record.active = is_default
        counter += 1
    return counter


def _mark_stale_models_inactive(
        records: list[AIModel],
        discovered_set: set[str]
    ) -> int:
    marked_inactive = 0
    for record in records:
        if record.model_id in discovered_set:
            continue
        if record.active:
            marked_inactive += 1
        record.active = False
    return marked_inactive


def sync_ai_models_with_local_inventory(
        app: Flask
    ) -> dict[str, int | str | None]:
    """Sync ai_models table to local instance/models folders and config default."""

    provider = normalize_provider_name(app.config.get("AI_PROVIDER")) or "huggingface"
    models_root = Path(app.instance_path) / "models"
    discovered_model_ids = _discover_model_ids(models_root)
    if provider == "ollama":
        default_model_id = str(
            app.config.get("AI_OLLAMA_MODEL")
            or app.config.get("AI_MODEL_NAME")
            or ""
        ).strip()
    else:
        default_model_id = str(app.config.get("AI_MODEL_NAME") or "").strip()

    records = (
        db.session.query(AIModel)
        .filter(AIModel.provider == provider)
        .all()
    )
    by_model_id = _index_records_by_model_id(records)

    discovered_set = set(discovered_model_ids)
    upserted = _upsert_discovered_models(
        provider=provider,
        models_root=models_root,
        discovered_model_ids=discovered_model_ids,
        by_model_id=by_model_id,
        default_model_id=default_model_id,
    )
    marked_inactive = _mark_stale_models_inactive(records, discovered_set)

    if default_model_id:
        default_record = by_model_id.get(default_model_id)
        if default_record is None:
            default_path = (models_root / default_model_id).resolve().as_posix()
            db.session.add(
                AIModel(
                    provider=provider,
                    model_id=default_model_id,
                    source="config_default",
                    path=default_path,
                    active=True,
                )
            )
            upserted += 1
        else:
            default_record.active = True

    db.session.commit()
    return {
        "provider": provider,
        "discovered": len(discovered_model_ids),
        "upserted": upserted,
        "marked_inactive": marked_inactive,
        "default_model_id": default_model_id or None,
    }