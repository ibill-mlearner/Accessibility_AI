from __future__ import annotations

from dataclasses import dataclass

from app.utils.env_config import parse_env, parse_json_object


def _to_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(slots=True)
class AIPipelineV2ModuleConfig:
    provider: str = "huggingface"
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    timeout_seconds: int = 60
    max_new_tokens: int = 256
    temperature: float = 0.7
    torch_dtype: str = "bfloat16"
    device_map: str = "auto"
    config_log_path: str = "ai_pipeline_v2_model_config.txt"
    ollama_endpoint: str = ""
    ollama_model_id: str = ""
    ollama_options: dict | None = None
    live_endpoint: str = ""
    huggingface_cache_dir: str | None = None
    enable_ollama_fallback: bool = True
    inventory_cache_ttl_seconds: int = 10

    @classmethod
    def from_env(cls) -> "AIPipelineV2ModuleConfig":
        return cls(
            provider=str(parse_env("AI_PROVIDER", "huggingface")).strip().lower(),
            model_name=str(parse_env("AI_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")).strip(),
            timeout_seconds=int(parse_env("AI_TIMEOUT_SECONDS", 60)),
            max_new_tokens=int(parse_env("AI_MAX_NEW_TOKENS", 256)),
            temperature=float(parse_env("AI_TEMPERATURE", 0.7, float)),
            torch_dtype=str(parse_env("AI_TORCH_DTYPE", "bfloat16")).strip().lower(),
            device_map=str(parse_env("AI_DEVICE_MAP", "auto")).strip(),
            config_log_path=str(parse_env("AI_CONFIG_LOG_PATH", "ai_pipeline_v2_model_config.txt")).strip(),
            ollama_endpoint=str(parse_env("AI_OLLAMA_ENDPOINT", "")).strip(),
            ollama_model_id=str(parse_env("AI_OLLAMA_MODEL", "")).strip(),
            ollama_options=parse_json_object("AI_OLLAMA_OPTIONS", None),
            live_endpoint=str(parse_env("AI_LIVE_ENDPOINT", "")).strip(),
            huggingface_cache_dir=(str(parse_env("AI_HUGGINGFACE_CACHE_DIR", "")).strip() or None),
            enable_ollama_fallback=_to_bool(parse_env("AI_ENABLE_OLLAMA_FALLBACK", True), True),
            inventory_cache_ttl_seconds=int(parse_env("AI_INVENTORY_CACHE_TTL_SECONDS", 10)),
        )

    def summary(self) -> dict[str, object]:
        return {
            "section": "ai_pipeline_v2",
            "provider": self.provider,
            "model_name": self.model_name,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
        }
