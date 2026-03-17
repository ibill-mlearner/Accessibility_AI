from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import logging
from pathlib import Path
from .interfaces import AIPipelineServiceInterface, AIProviderFactoryInterface
from .pipeline import AIPipelineConfig, AIPipelineService
from .providers import create_provider

logger = logging.getLogger(__name__)


def _validate_huggingface_local_only_config(config: Mapping[str, Any]) -> None:
    provider = str(config.get("AI_PROVIDER") or "").strip().lower()
    if provider != "huggingface":
        return

    model_name = str(config.get("AI_MODEL_NAME") or "").strip()
    model_path = Path(model_name).expanduser() if model_name else None
    if model_path and model_path.exists() and model_path.is_dir():
        return

    cache_dir = str(config.get("AI_HUGGINGFACE_CACHE_DIR") or "").strip() or "<unset>"
    raise ValueError(
        "Invalid AI runtime configuration: AI_PROVIDER=huggingface requires AI_MODEL_NAME "
        "to be an existing local model directory. "
        f"Current AI_MODEL_NAME={model_name!r}, AI_HUGGINGFACE_CACHE_DIR={cache_dir!r}."
    )

def build_ai_service_from_config(
        config: Mapping[str, Any],
        provider_factory: AIProviderFactoryInterface | None = None,
) -> AIPipelineServiceInterface:
    _validate_huggingface_local_only_config(config)
    provider = config["AI_PROVIDER"]
    ollama_endpoint = config.get("AI_OLLAMA_ENDPOINT")
    live_endpoint = config.get("AI_LIVE_ENDPOINT")
    logger.debug(
        "ai_pipeline.build_service request_id=%s provider=%s ollama_endpoint=%s live_endpoint=%s model_name=%s timeout_seconds=%s",
        "n/a",
        provider,
        bool(ollama_endpoint),
        bool(live_endpoint),
        config.get("AI_MODEL_NAME"),
        config.get("AI_TIMEOUT_SECONDS")
    )
    if provider in {"ollama", "ollama_local"} and not ollama_endpoint:
        raise ValueError("AI_OLLAMA_ENDPOINT must be configured when AI_PROVIDER=ollama")

    if provider in {"live", "live_agent", "http"} and not live_endpoint:
        raise ValueError("AI_LIVE_ENDPOINT must be configured for live endpoint providers")

    pipeline_config = AIPipelineConfig(
        provider=provider,
        model_name=config["AI_MODEL_NAME"],
        live_endpoint=live_endpoint or "",
        ollama_endpoint=ollama_endpoint or "",
        ollama_model_id=config.get("AI_OLLAMA_MODEL", config.get("AI_MODEL_NAME", "")),
        ollama_options=config.get("AI_OLLAMA_OPTIONS"),
        timeout_seconds=config["AI_TIMEOUT_SECONDS"],
        huggingface_model_id=config["AI_MODEL_NAME"],
        huggingface_cache_dir=config.get("AI_HUGGINGFACE_CACHE_DIR"),
        enable_ollama_fallback_on_hf_local_only_error=config.get("AI_ENABLE_OLLAMA_FALLBACK", True),
    )

    effective_provider_factory = provider_factory or create_provider

    provider_impl = effective_provider_factory(
        provider=pipeline_config.provider,
        model_name=pipeline_config.model_name,
        live_endpoint=pipeline_config.live_endpoint,
        ollama_endpoint=pipeline_config.ollama_endpoint,
        ollama_model_id=pipeline_config.ollama_model_id,
        ollama_options=pipeline_config.ollama_options,
        timeout_seconds=pipeline_config.timeout_seconds,
        huggingface_model_id=pipeline_config.huggingface_model_id,
        huggingface_cache_dir=pipeline_config.huggingface_cache_dir,
        max_new_tokens=pipeline_config.max_new_tokens,
        temperature=pipeline_config.temperature,
    )
    service = AIPipelineService(
        config=pipeline_config,
        provider=provider_impl,
        provider_factory=effective_provider_factory,
    )
    logger.debug(
        "ai_pipeline.build_service.ready request_id=%s provider=%s model=%s timeout_seconds=%s",
        "n/a",
        pipeline_config.provider,
        pipeline_config.model_name,
        pipeline_config.timeout_seconds
    )

    return service
