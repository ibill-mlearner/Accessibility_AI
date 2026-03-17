from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import AIPipelineV2ModuleConfig
from .service import AIPipelineService
from .types import AIPipelineConfig


def build_ai_service_from_config(
    module_config: AIPipelineV2ModuleConfig | None = None,
    *,
    config: Mapping[str, Any] | None = None,
    runtime_client_factory: Any | None = None,
    provider_factory: Any | None = None,
) -> AIPipelineService:
    _ = runtime_client_factory, provider_factory
    if module_config is None:
        source = config or {}
        module_config = AIPipelineV2ModuleConfig(
            model_id=str(source.get("AI_MODEL_NAME") or "meta-llama/Llama-3.2-3B-Instruct"),
            max_new_tokens=int(source.get("AI_MAX_NEW_TOKENS", 256)),
            temperature=float(source.get("AI_TEMPERATURE", 0.7)),
            config_log_path=str(source.get("AI_CONFIG_LOG_PATH") or "ai_pipeline_v2_model_config.txt"),
        )
    return AIPipelineService(
        AIPipelineConfig(
            model_id=module_config.model_id,
            max_new_tokens=module_config.max_new_tokens,
            temperature=module_config.temperature,
            config_log_path=module_config.config_log_path,
        )
    )
