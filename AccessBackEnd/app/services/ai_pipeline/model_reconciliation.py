from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ...extensions import db
from ...models import AIModel
from .model_inventory import ModelInventoryService


class AIModelReconciliationService:
    """Sync discovered model inventory into persistent ai_models rows."""

    _PROVIDER_PAYLOAD_KEYS = {
        "ollama": "ollama",
        "huggingface": "huggingface_local",
    }

    def __init__(self, inventory_service: ModelInventoryService) -> None:
        self.inventory_service = inventory_service

    def reconcile(self) -> dict[str, int]:
        payload = self.inventory_service.list_available_models()
        discovered = self._extract_discovered(payload)
        now = datetime.now(timezone.utc)

        existing_rows = db.session.execute(select(AIModel)).scalars().all()
        by_key = {(row.provider, row.model_id): row for row in existing_rows}

        upserted = 0
        activated = 0
        seen_keys: set[tuple[str, str]] = set()

        for item in discovered:
            key = (item["provider"], item["model_id"])
            seen_keys.add(key)
            row = by_key.get(key)
            if row is None:
                db.session.add(
                    AIModel(
                        provider=item["provider"],
                        model_id=item["model_id"],
                        source=item.get("source"),
                        path=item.get("path"),
                        last_seen_at=now,
                        active=True,
                    )
                )
                upserted += 1
                continue

            row.source = item.get("source") or row.source
            row.path = item.get("path") or row.path
            row.last_seen_at = now
            if not row.active:
                activated += 1
            row.active = True
            upserted += 1

        stale = 0
        for row in existing_rows:
            if (row.provider, row.model_id) in seen_keys:
                continue
            if row.active:
                row.active = False
                stale += 1

        db.session.commit()
        return {
            "upserted": upserted,
            "activated": activated,
            "stale_marked_inactive": stale,
            "discovered": len(discovered),
        }

    def _extract_discovered(self, payload: dict[str, Any]) -> list[dict[str, str | None]]:
        discovered: list[dict[str, str | None]] = []

        for provider, payload_key in self._PROVIDER_PAYLOAD_KEYS.items():
            provider_payload = payload.get(payload_key)
            if not isinstance(provider_payload, dict):
                continue

            models = provider_payload.get("models")
            if not isinstance(models, list):
                continue

            for model in models:
                if not isinstance(model, dict):
                    continue
                model_id = str(model.get("id") or "").strip()
                if not model_id:
                    continue
                discovered.append(
                    {
                        "provider": provider,
                        "model_id": model_id,
                        "source": str(model.get("source") or payload_key).strip() or payload_key,
                        "path": str(model.get("path") or "").strip() or None,
                    }
                )

        return discovered