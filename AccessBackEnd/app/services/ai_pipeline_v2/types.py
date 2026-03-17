from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIPipelineRequest:
    prompt: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None


@dataclass(slots=True)
class AIPipelineConfig:
    model_id: str = "meta-llama/Llama-3.2-3B-Instruct"
    max_new_tokens: int = 256
    temperature: float = 0.7
    torch_dtype: str = "bfloat16"
    device_map: str = "auto"
    config_log_path: str = "ai_pipeline_v2_model_config.txt"


@dataclass(slots=True)
class AIPipelineUpstreamError(RuntimeError):
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)
