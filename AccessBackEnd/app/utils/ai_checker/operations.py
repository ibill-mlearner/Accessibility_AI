from __future__ import annotations

from importlib import util
from pathlib import Path

from flask import Flask

from ...api.v1.routes import db
from ...models import AIModel
from .validators import AIInteractionValidator


class AIModelInventoryHelpers:
    @staticmethod
    def discover_model_ids(models_root: Path) -> list[str]:
        if not models_root.exists() or not models_root.is_dir():
            return []
        discovered: list[str] = []
        seen: set[str] = set()
        for child in sorted(models_root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            normalized = AIInteractionValidator.to_clean_model_id(child.name)
            model_id = normalized or str(child.name).strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            discovered.append(model_id)
        return discovered

    @staticmethod
    def resolve_local_models_root(app: Flask) -> Path:
        project_root = Path(app.root_path).resolve().parents[1]
        # Model inventory lookup order:
        # 1) Legacy thin runtime folder under the repo (if present).
        # 2) Installed ai_pipeline package models cache directory (if present).
        # 3) <app.instance_path>/models fallback.
        thin_models_root = project_root / "app" / "services" / "ai_pipeline_thin" / "models"
        if thin_models_root.exists() and thin_models_root.is_dir():
            return thin_models_root

        installed_models_root = AIModelInventoryHelpers.resolve_installed_pipeline_models_root()
        if installed_models_root is not None:
            return installed_models_root

        return Path(app.instance_path) / "models"

    @staticmethod
    def resolve_installed_pipeline_models_root() -> Path | None:
        spec = util.find_spec("ai_pipeline.model_loader")
        if spec is None or not spec.origin:
            return None

        models_root = Path(spec.origin).resolve().parent / "models"
        if not models_root.exists() or not models_root.is_dir():
            return None
        return models_root


class AIModelInventoryOperations:
    def __init__(self, app: Flask) -> None:
        self.app = app
        self.provider = AIInteractionValidator.to_clean_text(app.config.get("AI_PROVIDER"), lower=True)
        self.models_root = _resolve_local_models_root(app)

    def discover_local_model_inventory(self) -> dict[str, str | Path | list[str]]:
        discovered_model_ids = _discover_model_ids(self.models_root)
        return {
            "provider": self.provider,
            "models_root": self.models_root,
            "model_ids": discovered_model_ids,
        }

    def sync_ai_models_with_local_inventory(self) -> dict[str, int | str | None]:
        inventory = self.discover_local_model_inventory()
        provider = str(inventory["provider"])
        models_root = Path(inventory["models_root"])
        discovered_model_ids = list(inventory["model_ids"])
        default_model_id = str(self.app.config.get("AI_MODEL_NAME") or "").strip()

        records = db.session.query(AIModel).filter(AIModel.provider == provider).all()
        by_model_id = {record.model_id: record for record in records}
        discovered_set = set(discovered_model_ids)

        upserted = self._upsert_discovered_models(
            provider=provider,
            models_root=models_root,
            discovered_model_ids=discovered_model_ids,
            by_model_id=by_model_id,
            default_model_id=default_model_id,
        )

        marked_inactive = self._mark_missing_models_inactive(records=records, discovered_set=discovered_set)

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

    def _upsert_discovered_models(
        self,
        *,
        provider: str,
        models_root: Path,
        discovered_model_ids: list[str],
        by_model_id: dict[str, AIModel],
        default_model_id: str,
    ) -> int:
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
        return upserted

    def _mark_missing_models_inactive(self, *, records: list[AIModel], discovered_set: set[str]) -> int:
        marked_inactive = 0
        for record in records:
            if record.model_id in discovered_set:
                continue
            if record.active:
                marked_inactive += 1
            record.active = False
        return marked_inactive


def discover_local_model_inventory(app: Flask) -> dict[str, str | Path | list[str]]:
    return AIModelInventoryOperations(app).discover_local_model_inventory()


def sync_ai_models_with_local_inventory(app: Flask) -> dict[str, int | str | None]:
    return AIModelInventoryOperations(app).sync_ai_models_with_local_inventory()
_discover_model_ids = AIModelInventoryHelpers.discover_model_ids
_resolve_local_models_root = AIModelInventoryHelpers.resolve_local_models_root
_resolve_installed_pipeline_models_root = AIModelInventoryHelpers.resolve_installed_pipeline_models_root


__all__ = [
    "AIModelInventoryHelpers",
    "AIModelInventoryOperations",
    "discover_local_model_inventory",
    "sync_ai_models_with_local_inventory",
    "_discover_model_ids",
    "_resolve_local_models_root",
    "_resolve_installed_pipeline_models_root",
]
