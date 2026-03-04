from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Literal

ProviderId = Literal["ollama", "huggingface"]
ProviderPreference = Literal["any", "ollama", "huggingface"]


@dataclass(frozen=True, slots=True)
class ModelFamily:
    family_id: str
    label: str
    owner: str
    provider_candidates: Mapping[ProviderId, tuple[str, ...]]


MODEL_FAMILIES: tuple[ModelFamily, ...] = (
    ModelFamily(
        family_id="qwen2_5",
        label="Qwen 2.5",
        owner="Alibaba / Qwen",
        provider_candidates={
            "ollama": (
                "qwen2.5:7b-instruct",
                "qwen2.5:3b-instruct",
                "qwen2.5:latest",
            ),
            "huggingface": (
                "Qwen/Qwen2.5-7B-Instruct",
                "Qwen/Qwen2.5-3B-Instruct",
            ),
        },
    ),
    ModelFamily(
        family_id="llama3_2",
        label="Llama 3.2",
        owner="Meta",
        provider_candidates={
            "ollama": (
                "llama3.2:3b-instruct",
                "llama3.2:1b-instruct",
                "llama3.2:latest",
            ),
            "huggingface": (
                "meta-llama/Llama-3.2-3B-Instruct",
                "meta-llama/Llama-3.2-1B-Instruct",
            ),
        },
    ),
    ModelFamily(
        family_id="gemma3",
        label="Gemma 3",
        owner="Google",
        provider_candidates={
            "ollama": (
                "gemma3:12b",
                "gemma3:4b",
                "gemma3:latest",
            ),
            "huggingface": (
                "google/gemma-3-12b-it",
                "google/gemma-3-4b-it",
            ),
        },
    ),
    ModelFamily(
        family_id="phi4_mini",
        label="Phi-4 Mini",
        owner="Microsoft",
        provider_candidates={
            "ollama": (
                "phi4-mini:3.8b",
                "phi4-mini:latest",
            ),
            "huggingface": (
                "microsoft/Phi-4-mini-instruct",
            ),
        },
    ),
)

_FAMILY_BY_ID: dict[str, ModelFamily] = {family.family_id: family for family in MODEL_FAMILIES}


def get_model_catalog_metadata() -> list[dict[str, object]]:
    """Return serializable model-family metadata for API usage."""
    return [
        {
            "family_id": family.family_id,
            "label": family.label,
            "owner": family.owner,
            "providers": {
                provider: list(candidates)
                for provider, candidates in family.provider_candidates.items()
            },
        }
        for family in MODEL_FAMILIES
    ]


def family_id_from_model_id(model_id: str) -> str | None:
    """Map a concrete model_id to a known model family using candidate matching."""
    normalized = model_id.strip().lower()
    if not normalized:
        return None

    for family in MODEL_FAMILIES:
        for candidates in family.provider_candidates.values():
            if any(candidate.lower() == normalized for candidate in candidates):
                return family.family_id
    return None


def resolve_model_selection(
    *,
    provider: ProviderId | None = None,
    model_id: str | None = None,
    family_id: str | None = None,
    provider_preference: ProviderPreference = "any",
    available_model_ids: Mapping[str, Collection[str]] | None = None,
) -> dict[str, str]:
    """Resolve a concrete provider/model pair from explicit values or family preference."""
    if provider and model_id:
        if provider not in ("ollama", "huggingface"):
            raise ValueError(f"Unsupported provider: {provider}")
        if available_model_ids and not _is_available(provider, model_id, available_model_ids):
            raise ValueError(f"Model not available for provider {provider}: {model_id}")
        return {"provider": provider, "model_id": model_id}

    if not family_id:
        raise ValueError("family_id is required when provider/model_id are not provided")

    family = _FAMILY_BY_ID.get(family_id)
    if not family:
        raise ValueError(f"Unsupported family_id: {family_id}")

    for provider_id in _provider_order(provider_preference):
        candidates = family.provider_candidates.get(provider_id, ())
        for candidate in candidates:
            if available_model_ids and not _is_available(provider_id, candidate, available_model_ids):
                continue
            return {"provider": provider_id, "model_id": candidate, "family_id": family.family_id}

    raise ValueError(
        f"No candidate model available for family '{family.family_id}' with provider_preference '{provider_preference}'"
    )


def _provider_order(preference: ProviderPreference) -> tuple[ProviderId, ...]:
    if preference == "ollama":
        return ("ollama", "huggingface")
    if preference == "huggingface":
        return ("huggingface", "ollama")
    if preference == "any":
        return ("ollama", "huggingface")
    raise ValueError(f"Unsupported provider_preference: {preference}")


def _is_available(
    provider: ProviderId,
    model_id: str,
    available_model_ids: Mapping[str, Collection[str]],
) -> bool:
    available_for_provider = available_model_ids.get(provider)
    if not available_for_provider:
        return False
    normalized = {candidate.lower() for candidate in available_for_provider}
    return model_id.lower() in normalized