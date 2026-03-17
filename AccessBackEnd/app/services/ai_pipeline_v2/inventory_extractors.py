from __future__ import annotations

from typing import Any


def extract_huggingface_model_id_map(inventory_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    payload = inventory_payload or {}
    models = payload.get("models") if isinstance(payload.get("models"), list) else []
    mapping: dict[str, dict[str, Any]] = {}
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = str(model.get("id") or "").strip()
        if model_id:
            mapping[model_id] = model
    return mapping
