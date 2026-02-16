from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .providers import (
    AIProvider,
    HTTPEndpointProvider,
    HuggingFaceLangChainProvider,
    MockJSONProvider,
    OllamaProvider,
)
from .types import PipelineRequest, PipelineResponse


@dataclass(slots=True)
class AIPipelineConfig:
    """Runtime configuration for AI pipeline provider selection.

    # Logic intent:
    # - Keep configuration serializable and easy to pass from app config/env.
    # - Allow this package to be imported by a hello-world script with minimal setup.
    """

    provider: str = "ollama"
    mock_resource_path: str = ""
    live_endpoint: str = ""
    ollama_endpoint: str = ""
    ollama_model_id: str = ""
    ollama_options: dict[str, Any] | None = None
    timeout_seconds: int = 60
    huggingface_model_id: str = ""
    huggingface_cache_dir: str | None = None
    max_new_tokens: int = 256
    temperature: float = 0.1


class AIPipelineService:
    """High-level orchestration service for JSON-first AI interactions.

    # Logic intent:
    # - Accept plain text prompts + context and always return JSON data.
    # - Isolate provider concerns behind a stable API (`run_interaction`).
    # - Keep architecture package-ready for reuse outside this repository.
    """

    def __init__(self, config: AIPipelineConfig) -> None:
        # Logic intent:
        # 1) Store config once.
        # 2) Construct provider client once for efficient repeated calls.
        self.config = config
        self._provider = self._build_provider(config)

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None) -> dict:
        # Logic intent:
        # 1) Wrap raw inputs in a typed request object.
        # 2) Invoke provider and validate JSON shape.
        # 3) Return a normalized dictionary with consistent metadata.
        request = PipelineRequest(prompt=prompt, context=context or {})
        payload = self._provider.invoke(request)

        if not isinstance(payload, dict):
            raise TypeError("Pipeline provider must return a dictionary")

        meta = payload.setdefault("meta", {})
        if not isinstance(meta, dict):
            payload["meta"] = {"warning": "provider returned invalid meta payload"}
            meta = payload["meta"]

        response = PipelineResponse(
            data={k: v for k, v in payload.items() if k != "meta"},
            meta={
                **meta,
                "pipeline": "app.services.ai_pipeline",
                "selected_provider": self.config.provider,
            },
        )
        return {**response.data, "meta": response.meta}

    def _build_provider(self, config: AIPipelineConfig) -> AIProvider:
        # Logic intent:
        # - Route configured provider aliases to concrete provider implementations.
        provider = (config.provider or "ollama").strip().lower()

        if provider in {"mock", "mock_json", "json"}:
            return MockJSONProvider(mock_resource_path=config.mock_resource_path)

        if provider in {"ollama", "ollama_local"}:
            return OllamaProvider(
                endpoint=config.ollama_endpoint or config.live_endpoint,
                model_id=config.ollama_model_id or config.huggingface_model_id,
                options=config.ollama_options,
                timeout_seconds=config.timeout_seconds,
            )

        if provider in {"live", "live_agent", "http"}:
            return HTTPEndpointProvider(endpoint=config.live_endpoint, timeout_seconds=config.timeout_seconds)

        if provider in {"hf", "huggingface", "langchain_hf"}:
            return HuggingFaceLangChainProvider(
                model_id=config.huggingface_model_id,
                cache_dir=config.huggingface_cache_dir,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
            )

        raise ValueError(f"Unsupported AI provider: {config.provider}")
