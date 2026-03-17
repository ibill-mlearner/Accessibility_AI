from __future__ import annotations

from dataclasses import dataclass

from app.utils.env_config import parse_env, parse_positive_int


@dataclass(slots=True)
class AIPipelineV2ModuleConfig:
    model_id: str = "meta-llama/Llama-3.2-3B-Instruct"
    max_new_tokens: int = 256
    temperature: float = 0.7
    config_log_path: str = "ai_pipeline_v2_model_config.txt"

    @classmethod
    def from_env(cls) -> "AIPipelineV2ModuleConfig":
        return cls(
            model_id=str(parse_env("AI_MODEL_NAME", "meta-llama/Llama-3.2-3B-Instruct")),
            max_new_tokens=parse_positive_int("AI_MAX_NEW_TOKENS", 256),
            temperature=float(parse_env("AI_TEMPERATURE", 0.7, float)),
            config_log_path=str(parse_env("AI_CONFIG_LOG_PATH", "ai_pipeline_v2_model_config.txt")),
        )

    def summary(self) -> dict[str, object]:
        return {"section": "ai_pipeline_v2", "model_id": self.model_id}
