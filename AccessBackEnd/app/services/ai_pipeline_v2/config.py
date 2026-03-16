from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.utils.env_config import parse_env, parse_json_object, parse_positive_int


def default_ai_model_name() -> str:
    instance_dir = Path(__file__).resolve().parents[3] / "instance"
    local_default = instance_dir / "models" / "Qwen2.5-0.5B-Instruct"
    if parse_env("AI_HUGGINGFACE_ALLOW_DOWNLOAD", False, bool):
        return "Qwen/Qwen2.5-0.5B-Instruct"
    return str(local_default)


@dataclass(slots=True)
class AIPipelineV2ModuleConfig:
    provider: str = "ollama"
    model_name: str = ""
    ollama_endpoint: str = "http://localhost:11434/api/chat"
    live_endpoint: str = "http://localhost:11434/api/chat"
    ollama_model_id: str = ""
    ollama_options: dict | None = None
    timeout_seconds: int = 60
    huggingface_model_id: str = ""
    huggingface_cache_dir: str | None = None
    huggingface_allow_download: bool = False
    enable_ollama_fallback: bool = False
    inventory_cache_ttl_seconds: int = 30

    @classmethod
    def from_env(cls) -> "AIPipelineV2ModuleConfig":
        model_name = parse_env("AI_MODEL_NAME", default_ai_model_name())
        ollama_endpoint = parse_env("AI_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")
        return cls(
            provider=parse_env("AI_PROVIDER", "ollama"),
            model_name=model_name,
            ollama_endpoint=ollama_endpoint,
            live_endpoint=parse_env("AI_LIVE_ENDPOINT", ollama_endpoint),
            ollama_model_id=parse_env("AI_OLLAMA_MODEL", model_name),
            ollama_options=parse_json_object("AI_OLLAMA_OPTIONS", {}),
            timeout_seconds=parse_positive_int("AI_TIMEOUT_SECONDS", 60),
            huggingface_model_id=model_name,
            huggingface_cache_dir=parse_env("AI_HUGGINGFACE_CACHE_DIR"),
            huggingface_allow_download=parse_env("AI_HUGGINGFACE_ALLOW_DOWNLOAD", False, bool),
            enable_ollama_fallback=parse_env("AI_ENABLE_OLLAMA_FALLBACK", False, bool),
            inventory_cache_ttl_seconds=parse_positive_int("AI_INVENTORY_CACHE_TTL_SECONDS", 30),
        )

    def summary(self) -> dict[str, object]:
        return {
            "section": "ai_pipeline_v2",
            "provider": self.provider,
            "has_model": bool(self.model_name),
            "hf_download": self.huggingface_allow_download,
            "hf_cache_dir": self.huggingface_cache_dir,
        }
