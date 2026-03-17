from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.utils.env_config import normalize_backend_relative_dir, parse_env, parse_positive_int


def default_ai_model_name() -> str:
    local_default = Path("instance") / "models" / "Qwen2.5-0.5B-Instruct"
    return str(local_default)


@dataclass(slots=True)
class AIPipelineV2ModuleConfig:
    provider: str = "huggingface"
    model_name: str = ""
    ollama_endpoint: str = "http://localhost:11434/api/chat"
    live_endpoint: str = "http://localhost:11434/api/chat"
    ollama_model_id: str = ""
    ollama_options: dict | None = None
    timeout_seconds: int = 60
    huggingface_model_id: str = ""
    huggingface_cache_dir: str | None = None
    enable_ollama_fallback: bool = False
    inventory_cache_ttl_seconds: int = 30

    @classmethod
    def from_env(cls) -> "AIPipelineV2ModuleConfig":
        model_name = normalize_backend_relative_dir(parse_env("AI_MODEL_NAME", default_ai_model_name())) or ""
        ollama_endpoint = parse_env("AI_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")
        provider = str(parse_env("AI_PROVIDER", "huggingface") or "huggingface").strip().lower()
        if not provider:
            provider = "huggingface"
        enable_ollama_fallback = parse_env("AI_ENABLE_OLLAMA_FALLBACK", False, bool)

        return cls(
            provider=provider,
            model_name=model_name,
            ollama_endpoint="",
            live_endpoint="",
            ollama_model_id="",
            ollama_options={},
            timeout_seconds=parse_positive_int("AI_TIMEOUT_SECONDS", 60),
            huggingface_model_id=model_name,
            huggingface_cache_dir=parse_env("AI_HUGGINGFACE_CACHE_DIR"),
            enable_ollama_fallback=enable_ollama_fallback,
            inventory_cache_ttl_seconds=parse_positive_int("AI_INVENTORY_CACHE_TTL_SECONDS", 30),
        )

    def summary(self) -> dict[str, object]:
        return {
            "section": "ai_pipeline_v2",
            "provider": self.provider,
            "has_model": bool(self.model_name),
            "hf_cache_dir": self.huggingface_cache_dir,
        }
