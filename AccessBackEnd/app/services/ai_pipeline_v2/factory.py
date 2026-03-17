from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import AIPipelineV2ModuleConfig
from .service import AIPipelineService
from .types import AIPipelineConfig


def _module_config_from_mapping(config: Mapping[str, Any]) -> AIPipelineV2ModuleConfig:
    return AIPipelineV2ModuleConfig(
        provider=str(config.get("AI_PROVIDER") or "huggingface").strip().lower(),
        model_name=str(config.get("AI_MODEL_NAME") or "meta-llama/Llama-3.2-3B-Instruct").strip(),
        timeout_seconds=int(config.get("AI_TIMEOUT_SECONDS", 60)),
        max_new_tokens=int(config.get("AI_MAX_NEW_TOKENS", 256)),
        temperature=float(config.get("AI_TEMPERATURE", 0.7)),
        torch_dtype=str(config.get("AI_TORCH_DTYPE") or "bfloat16").strip().lower(),
        device_map=str(config.get("AI_DEVICE_MAP") or "auto").strip(),
        config_log_path=str(config.get("AI_CONFIG_LOG_PATH") or "ai_pipeline_v2_model_config.txt").strip(),
        ollama_endpoint=str(config.get("AI_OLLAMA_ENDPOINT") or "").strip(),
        ollama_model_id=str(config.get("AI_OLLAMA_MODEL") or "").strip(),
        ollama_options=config.get("AI_OLLAMA_OPTIONS") if isinstance(config.get("AI_OLLAMA_OPTIONS"), dict) else None,
        live_endpoint=str(config.get("AI_LIVE_ENDPOINT") or "").strip(),
        huggingface_cache_dir=(str(config.get("AI_HUGGINGFACE_CACHE_DIR") or "").strip() or None),
        enable_ollama_fallback=bool(config.get("AI_ENABLE_OLLAMA_FALLBACK", True)),
        inventory_cache_ttl_seconds=int(config.get("AI_INVENTORY_CACHE_TTL_SECONDS", 10)),
    )


def build_ai_service_from_config(
    module_config: AIPipelineV2ModuleConfig | None = None,
    *,
    config: Mapping[str, Any] | None = None,
    runtime_client_factory: Any | None = None,
    provider_factory: Any | None = None,
) -> AIPipelineService:
    resolved = module_config or _module_config_from_mapping(config or {})

    return AIPipelineService(
        AIPipelineConfig(
            model_id=resolved.model_name,
            max_new_tokens=resolved.max_new_tokens,
            temperature=resolved.temperature,
            torch_dtype=resolved.torch_dtype,
            device_map=resolved.device_map,
            config_log_path=resolved.config_log_path,
        ),
        runtime_client_factory=runtime_client_factory,
        provider_factory=provider_factory,
    )
