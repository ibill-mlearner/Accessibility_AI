from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ASSISTANT_TEXT_KEYS: tuple[str, ...] = (
    "assistant_text",
    "result",
    "answer",
    "response_text",
    "response",
    "output",
    "text",
)


@dataclass(slots=True)
class AIPipelineRequest:
    prompt: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    chat_id: int | None = None
    initiated_by: str | None = None
    class_id: int | None = None
    user_id: int | str | None = None
    rag: dict[str, Any] | None = None
    request_id: str | None = None


@dataclass(slots=True)
class AIPipelineConfig:
    provider: str = "huggingface"
    model_name: str = ""
    live_endpoint: str = ""
    # Deprecated: Ollama has been removed from the active MVP runtime.
    ollama_endpoint: str = ""
    ollama_model_id: str = ""
    ollama_options: dict[str, Any] | None = None
    timeout_seconds: int = 60
    huggingface_model_id: str = ""
    huggingface_cache_dir: str | None = None
    huggingface_allow_download: bool = False
    # Deprecated: fallback is disabled because Ollama is no longer used.
    enable_ollama_fallback_on_hf_local_only_error: bool = False
    inventory_cache_ttl_seconds: int = 30
    max_new_tokens: int = 256
    temperature: float = 0.1


@dataclass(slots=True)
class AIPipelineUpstreamError(RuntimeError):
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)
