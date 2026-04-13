from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask

from ..extensions import db
from ..models import AIModel
from ..utils.ai_checker.model_artifacts import has_valid_model_artifacts
from ..utils.ai_checker.operations import discover_local_model_inventory
from ..utils.ai_checker.validators import AIInteractionValidator


class ModelFileLoader:
    """DB-layer model inventory loader and presenter."""

    def __init__(self, app: Flask) -> None:
        self._app = app

    def format_and_validate_model_name(self, raw_name: str, *, models_root: Path) -> tuple[str, str]:
        normalized = AIInteractionValidator.to_clean_model_id(raw_name)
        if not normalized:
            return "", ""
        candidate_dir = models_root / raw_name
        if not candidate_dir.exists() or not candidate_dir.is_dir():
            return "", ""
        if not has_valid_model_artifacts(candidate_dir):
            return "", ""

        # Map local cache folder slugs to canonical repo ids when possible.
        if normalized == raw_name and "--" in raw_name and "/" not in raw_name:
            normalized = raw_name.replace("--", "/")

        if "/" not in normalized:
            config_path = candidate_dir / "config.json"
            if config_path.exists():
                try:
                    payload = json.loads(config_path.read_text(encoding="utf-8"))
                    name_or_path = AIInteractionValidator.to_clean_model_id((payload or {}).get("_name_or_path"))
                    if "/" in name_or_path:
                        normalized = name_or_path
                except Exception:
                    pass

        if "/" not in normalized:
            return "", ""
        return normalized, candidate_dir.as_posix()

    def query_folder_and_update_database(self) -> dict[str, Any]:
        inventory = discover_local_model_inventory(self._app)
        provider = str(inventory.get("provider") or "").strip().lower()
        models_root = Path(inventory["models_root"])
        discovered_raw_ids = [child.name for child in models_root.iterdir() if child.is_dir()] if models_root.exists() and models_root.is_dir() else []
        validated_models: dict[str, str] = {}
        for raw_id in discovered_raw_ids:
            model_id, resolved_path = self.format_and_validate_model_name(str(raw_id), models_root=models_root)
            if not model_id:
                continue
            validated_models[model_id] = resolved_path
        discovered_set = set(validated_models.keys())

        records = db.session.query(AIModel).filter(AIModel.provider == provider).all()
        by_model_id = {str(record.model_id): record for record in records}
        upserted = 0

        for model_id in sorted(discovered_set):
            record = by_model_id.get(model_id)
            path = validated_models.get(model_id, (models_root / model_id).as_posix())
            if record is None:
                db.session.add(AIModel(provider=provider, model_id=model_id, source="model_file_loader", path=path, active=False))
                upserted += 1
                continue
            record.source = "model_file_loader"
            record.path = path
            upserted += 1

        deactivated = 0
        for record in records:
            if record.model_id in discovered_set:
                continue
            if record.active:
                deactivated += 1
            record.active = False

        db.session.commit()
        return {
            "provider": provider,
            "models_root": models_root.as_posix(),
            "discovered": len(discovered_set),
            "upserted": upserted,
            "deactivated": deactivated,
        }

    def deliver_models_from_database(self) -> dict[str, Any]:
        provider = AIInteractionValidator.to_clean_text(self._app.config.get("AI_PROVIDER"), lower=True)
        rows = (
            db.session.query(AIModel)
            .filter(AIModel.provider == provider)
            .order_by(AIModel.active.desc(), AIModel.model_id.asc())
            .all()
        )
        models = []
        for row in rows:
            model_id = str(row.model_id or "").strip()
            if not model_id:
                continue
            if model_id == ".locks":
                continue
            models.append({"id": model_id})
        return {
            "model_defaults": {"provider": provider, "model_name": str(self._app.config.get("AI_MODEL_NAME") or "").strip()},
            "local": {"models": models, "count": len(models)},
            "huggingface_local": {"models": models, "count": len(models)},
        }
