from __future__ import annotations

from typing import Any

from .types import AIPipelineUpstreamError


def normalize_provider_name(provider: str | None) -> str:
    _ = provider
    return "huggingface"


def map_exception(exc: Exception, *, source: str = "provider_runtime") -> AIPipelineUpstreamError:
    return AIPipelineUpstreamError(str(exc) or "AI provider execution failed", details={"source": source})


def normalize_backend_response(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    return {"assistant_text": str(raw)}


class HuggingFaceBackend:
    def __init__(self, config: Any | None = None, model_id: str | None = None) -> None:
        self.config = config
        self.model_id = model_id

    def name(self) -> str:
        return "huggingface"
