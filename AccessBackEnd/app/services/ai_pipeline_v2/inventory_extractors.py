from __future__ import annotations

from typing import Any, Callable


def extract_huggingface_model_id_map(
    payload: dict[str, Any],
    *,
    normalize: Callable[[str], str] | None = None,
) -> dict[str, set[str]]:
    """
    Build provider->model-id sets from inventory payloads using model `id` only.
    This keeps selection logic independent of optional runtime fields like
    path/size/source and supports both migration-era bucket names.
    Output is normalized to a single provider key: `huggingface`.
    """
    provider_models: dict[str, set[str]] = {"huggingface": set()}

    for top_key in ("huggingface_local", "local"):
        provider_payload = payload.get(top_key)
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
            normalized = normalize(model_id) if normalize is not None else model_id
            if normalized:
                provider_models["huggingface"].add(normalized)

    return provider_models
