from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask

from ..extensions import db
from ..models import AIModel
from ..utils.ai_checker.operations import discover_local_model_inventory
from ..utils.ai_checker.validators import AIInteractionValidator
from .utilities import ModelFileLoaderDBUtilities


class ModelFileLoader:
    """DB-layer model inventory loader and presenter."""

    def __init__(self, app: Flask) -> None:
        self._app = app
        self._database_utilities = ModelFileLoaderDBUtilities()

    def format_and_validate_model_name(self, raw_name: str, *, models_root: Path) -> tuple[str, str]:
        normalized = AIInteractionValidator.to_clean_model_id(raw_name)
        candidate_dir = models_root / raw_name
        if not self._database_utilities.is_valid_model_candidate(normalized, candidate_dir=candidate_dir):
            return self._database_utilities.empty_model_validation_result()

        # Map ai_checker/local-cache folder slugs (for example org--model) to canonical HF ids (org/model).
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
                except Exception as exc:
                    self._app.logger.debug(
                        "db.model_file_loader.config_parse_failed model_dir=%s error=%s",
                        candidate_dir.as_posix(),
                        exc.__class__.__name__,
                    )

        if "/" not in normalized:
            return self._database_utilities.empty_model_validation_result()
        return normalized, candidate_dir.as_posix()

    def query_folder_and_update_database(self) -> dict[str, Any]:
        inventory = discover_local_model_inventory(self._app)
        provider = str(inventory.get("provider") or "").strip().lower()
        models_root = Path(inventory["models_root"])
        discovered_raw_ids = [child.name for child in models_root.iterdir() if child.is_dir()] if models_root.exists() and models_root.is_dir() else []
        validated_models = self._database_utilities.collect_validated_models(
            discovered_raw_ids=discovered_raw_ids,
            models_root=models_root,
            formatter=self.format_and_validate_model_name,
        )
        discovered_set = set(validated_models.keys())

        records = db.session.query(AIModel).filter(AIModel.provider == provider).all()
        upserted = self._database_utilities.upsert_provider_models(
            records=records,
            provider=provider,
            discovered_set=discovered_set,
            validated_models=validated_models,
            models_root=models_root,
            add_record=db.session.add,
        )
        deactivated = self._database_utilities.deactivate_missing_models(records=records, discovered_set=discovered_set)

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
