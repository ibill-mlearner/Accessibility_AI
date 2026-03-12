from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .interfaces import AIProviderFactoryInterface
from .providers import HuggingFaceProvider, HttpProvider, OllamaProvider, normalize_provider_name
from .service import AIPipelineService
from .types import AIPipelineConfig


def create_provider(config: AIPipelineConfig, *, provider: str, model_id: str):
    selected = normalize_provider_name(provider)
    if selected == "ollama":
        endpoint = config.ollama_endpoint or config.live_endpoint
        return OllamaProvider(config=config, model_id=model_id, endpoint=endpoint)
    if selected == "http":
        return HttpProvider(config=config, model_id=model_id, endpoint=config.live_endpoint)
    if selected == "huggingface":
        return HuggingFaceProvider(config=config, model_id=model_id)
    raise ValueError(f"Unsupported AI provider: {provider}")


def _validate_huggingface_local_only_config(config: Mapping[str, Any]) -> None:
    provider = normalize_provider_name(str(config.get("AI_PROVIDER") or ""))
    if provider != "huggingface" or bool(config.get("AI_HUGGINGFACE_ALLOW_DOWNLOAD", False)):
        return
    model_name = str(config.get("AI_MODEL_NAME") or "").strip()
    model_path = Path(model_name).expanduser() if model_name else None
    if model_path and model_path.exists() and model_path.is_dir():
        return
    raise ValueError(
        "Invalid AI runtime configuration: AI_PROVIDER=huggingface with local-only mode requires "
        "AI_MODEL_NAME to be an existing local model directory."
    )


def build_ai_service_from_config(
    config: Mapping[str, Any],
    provider_factory: AIProviderFactoryInterface | None = None,
) -> AIPipelineService:
    _validate_huggingface_local_only_config(config)
    pipeline_config = AIPipelineConfig(
        provider=str(config["AI_PROVIDER"]),
        model_name=str(config.get("AI_MODEL_NAME") or ""),
        live_endpoint=str(config.get("AI_LIVE_ENDPOINT") or ""),
        ollama_endpoint=str(config.get("AI_OLLAMA_ENDPOINT") or ""),
        ollama_model_id=str(config.get("AI_OLLAMA_MODEL") or config.get("AI_MODEL_NAME") or ""),
        ollama_options=config.get("AI_OLLAMA_OPTIONS"),
        timeout_seconds=int(config.get("AI_TIMEOUT_SECONDS", 60)),
        huggingface_model_id=str(config.get("AI_MODEL_NAME") or ""),
        huggingface_cache_dir=config.get("AI_HUGGINGFACE_CACHE_DIR"),
        huggingface_allow_download=bool(config.get("AI_HUGGINGFACE_ALLOW_DOWNLOAD", False)),
        enable_ollama_fallback_on_hf_local_only_error=bool(config.get("AI_ENABLE_OLLAMA_FALLBACK", True)),
    )
    service = AIPipelineService(config=pipeline_config, provider_factory=provider_factory or create_provider)
    return service
