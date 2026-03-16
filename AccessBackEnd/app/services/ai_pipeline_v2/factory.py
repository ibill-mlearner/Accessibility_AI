from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .config import AIPipelineV2ModuleConfig
from .interfaces import AIProviderFactoryInterface
from .providers import HuggingFaceBackend
from .service import AIPipelineService
from .types import AIPipelineConfig


def _validate_huggingface_cache_dir_writable(config: AIPipelineV2ModuleConfig) -> None:
    cache_dir_raw = str(config.huggingface_cache_dir or "").strip()
    if not cache_dir_raw:
        return
    cache_dir = Path(cache_dir_raw).expanduser()
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "Invalid AI runtime configuration: AI_HUGGINGFACE_CACHE_DIR must be writable."
        ) from exc
    if not cache_dir.is_dir():
        raise ValueError(
            "Invalid AI runtime configuration: AI_HUGGINGFACE_CACHE_DIR must be a directory."
        )
    probe = cache_dir / ".write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "Invalid AI runtime configuration: AI_HUGGINGFACE_CACHE_DIR must be writable."
        ) from exc


def _validate_huggingface_local_only_config(config: AIPipelineV2ModuleConfig) -> None:
    if config.huggingface_allow_download:
        return
    model_name = str(config.model_name).strip()
    model_path = Path(model_name).expanduser() if model_name else None
    if model_path and model_path.exists() and model_path.is_dir():
        return
    raise ValueError(
        "Invalid AI runtime configuration: AI_PROVIDER=huggingface local-only mode requires AI_MODEL_NAME to be an existing local model directory."
    )


def _module_config_from_mapping(config: Mapping[str, Any]) -> AIPipelineV2ModuleConfig:
    model_name = str(config.get("AI_MODEL_NAME") or "").strip()
    return AIPipelineV2ModuleConfig(
        provider="local",
        model_name=model_name,
        live_endpoint="",
        ollama_endpoint="",
        ollama_model_id="",
        ollama_options={},
        timeout_seconds=int(config.get("AI_TIMEOUT_SECONDS", 60)),
        huggingface_model_id=model_name,
        huggingface_cache_dir=config.get("AI_HUGGINGFACE_CACHE_DIR"),
        huggingface_allow_download=bool(config.get("AI_HUGGINGFACE_ALLOW_DOWNLOAD", False)),
        enable_ollama_fallback=False,
        inventory_cache_ttl_seconds=int(config.get("AI_INVENTORY_CACHE_TTL_SECONDS", 30)),
    )


def build_ai_service_from_config(
    module_config: AIPipelineV2ModuleConfig | None = None,
    *,
    config: Mapping[str, Any] | None = None,
    runtime_client_factory: AIProviderFactoryInterface | None = None,
    provider_factory: AIProviderFactoryInterface | None = None,
) -> AIPipelineService:
    resolved_module = module_config or _module_config_from_mapping(config or {})
    _validate_huggingface_cache_dir_writable(resolved_module)
    _validate_huggingface_local_only_config(resolved_module)
    pipeline_config = AIPipelineConfig(
        provider=resolved_module.provider,
        model_name=resolved_module.model_name,
        live_endpoint=resolved_module.live_endpoint,
        ollama_endpoint=resolved_module.ollama_endpoint,
        ollama_model_id=resolved_module.ollama_model_id,
        ollama_options=resolved_module.ollama_options,
        timeout_seconds=resolved_module.timeout_seconds,
        huggingface_model_id=resolved_module.huggingface_model_id,
        huggingface_cache_dir=resolved_module.huggingface_cache_dir,
        huggingface_allow_download=resolved_module.huggingface_allow_download,
        enable_ollama_fallback_on_hf_local_only_error=resolved_module.enable_ollama_fallback,
        inventory_cache_ttl_seconds=resolved_module.inventory_cache_ttl_seconds,
    )
    service = AIPipelineService(
        config=pipeline_config,
        runtime_client_factory=runtime_client_factory or provider_factory or (lambda cfg, *, model_id: HuggingFaceBackend(config=cfg, model_id=model_id)),
    )
    return service
