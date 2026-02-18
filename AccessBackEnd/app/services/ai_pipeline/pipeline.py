from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import invoke_provider_or_raise
from .providers import (
    AIProvider,
    HTTPEndpointProvider,
    HuggingFaceLangChainProvider,
    MockJSONProvider,
    OllamaProvider,
)
from .types import PipelineRequest, PipelineResponse

_ASSISTANT_TEXT_KEYS: tuple[str, ...] = (
    "assistant_text",
    "result",
    "answer",
    "response_text",
    "response",
    "output",
    "text",
)


@dataclass(slots=True)
class AIPipelineConfig:
    """Runtime configuration for AI pipeline provider selection.

    # Logic intent:
    # - Keep configuration serializable and easy to pass from app config/env.
    # - Allow this package to be imported by a hello-world script with minimal setup.
    """

    provider: str = "ollama"
    model_name: str = ""
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

    def run_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> dict:
        # Logic intent:
        # 1) Accept optional metadata kwargs (for API/logger compatibility)
        #    without coupling the core pipeline to logging concerns.
        # 2) Wrap raw inputs in a typed request object.
        # 3) Invoke provider and validate JSON shape.
        # 4) Return a normalized dictionary with consistent metadata.
        _ = metadata
        request = PipelineRequest(prompt=prompt, context=context or {})
        payload = invoke_provider_or_raise(self._provider, request)

        meta = payload.setdefault("meta", {})
        if not isinstance(meta, dict):
            payload["meta"] = {"warning": "provider returned invalid meta payload"}
            meta = payload["meta"]

        # Keep canonical response keys centralized so API routes can pass through safely.
        response_data = self._canonicalize_provider_payload(payload)

        response = PipelineResponse(
            data=response_data,
            meta={
                **meta,
                "model": meta.get("model") or meta.get("model_id") or self.config.model_name,
                "pipeline": "app.services.ai_pipeline",
                "selected_provider": self.config.provider,
            },
        )
        return {**response.data, "meta": response.meta}

    @staticmethod
    def _canonicalize_provider_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Map provider-specific payload keys into a stable UI contract."""
        assistant_text = ""
        for key in _ASSISTANT_TEXT_KEYS:
            value = payload.get(key)
            if value is not None:
                assistant_text = str(value)
                break

        confidence_value = payload.get("confidence")
        confidence = float(confidence_value) if isinstance(confidence_value, (int, float)) else None

        notes_value = payload.get("notes")
        if isinstance(notes_value, list):
            notes = [str(note) for note in notes_value]
        elif isinstance(notes_value, str) and notes_value.strip():
            notes = [notes_value.strip()]
        else:
            notes = []

        return {
            "assistant_text": assistant_text,
            "confidence": confidence,
            "notes": notes,
        }

    def _build_provider(self, config: AIPipelineConfig) -> AIProvider:
        # Logic intent:
        # - Route configured provider aliases to concrete provider implementations.
        provider = (config.provider or "ollama").strip().lower()

        if provider in {"mock", "mock_json", "json"}:
            return MockJSONProvider(mock_resource_path=config.mock_resource_path)

        if provider in {"ollama", "ollama_local"}:
            return OllamaProvider(
                endpoint=config.ollama_endpoint or config.live_endpoint,
                model_id=config.ollama_model_id or config.model_name or config.huggingface_model_id,
                options=config.ollama_options,
                timeout_seconds=config.timeout_seconds,
            )

        if provider in {"live", "live_agent", "http"}:
            return HTTPEndpointProvider(
                endpoint=config.live_endpoint,
                model_name=config.model_name,
                timeout_seconds=config.timeout_seconds,
            )

        if provider in {"hf", "huggingface", "langchain_hf"}:
            return HuggingFaceLangChainProvider(
                model_id=config.huggingface_model_id,
                cache_dir=config.huggingface_cache_dir,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
            )

        raise ValueError(f"Unsupported AI provider: {config.provider}")
