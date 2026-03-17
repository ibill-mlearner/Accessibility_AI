from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.utils.env_config import parse_env, parse_positive_int


def default_ai_model_name() -> str:
    instance_dir = Path(__file__).resolve().parents[3] / "instance"
    local_default = instance_dir / "models" / "Qwen2.5-0.5B-Instruct"
    return str(local_default)


@dataclass(slots=True)
class AIPipelineSlimModuleConfig:
    provider: str = "huggingface"
    model_name: str = ""
    timeout_seconds: int = 60
    huggingface_cache_dir: str | None = None
    enable_ollama_fallback: bool = False
    inventory_cache_ttl_seconds: int = 30
    live_endpoint: str = ""
    ollama_endpoint: str = ""
    ollama_model_id: str = ""
    ollama_options: dict | None = None
    huggingface_model_id: str = ""

    @classmethod
    def from_env(cls) -> "AIPipelineSlimModuleConfig":
        model_name = parse_env("AI_MODEL_NAME", default_ai_model_name())
        provider = str(parse_env("AI_PROVIDER", "huggingface") or "huggingface").strip().lower()
        if not provider:
            provider = "huggingface"
        enable_ollama_fallback = parse_env("AI_ENABLE_OLLAMA_FALLBACK", False, bool)

        return cls(
            provider=provider,
            model_name=model_name,
            timeout_seconds=parse_positive_int("AI_TIMEOUT_SECONDS", 60),
            huggingface_cache_dir=parse_env("AI_HUGGINGFACE_CACHE_DIR"),
            enable_ollama_fallback=enable_ollama_fallback,
            inventory_cache_ttl_seconds=parse_positive_int("AI_INVENTORY_CACHE_TTL_SECONDS", 30),
            live_endpoint="",
            ollama_endpoint="",
            ollama_model_id=model_name,
            ollama_options={},
            huggingface_model_id=model_name,
        )

    def summary(self) -> dict[str, object]:
        return {
            "section": "ai_pipeline_slim",
            "provider": self.provider,
            "has_model": bool(self.model_name),
            "hf_cache_dir": self.huggingface_cache_dir,
        }
