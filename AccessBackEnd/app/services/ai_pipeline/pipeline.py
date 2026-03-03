from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import invoke_provider_or_raise
from .model_inventory import ModelInventoryConfig, ModelInventoryService
from .providers import (
    AIProvider,
    HTTPEndpointProvider,
    HuggingFaceLangChainProvider,
    MockJSONProvider,
    OllamaProvider,
)
from .types import PipelineRequest, PipelineResponse, AIPipelineRequest

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

    provider: str = "ollama" #defaults to ollama
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

def run(self, request: AIPipelineRequest) -> dict:
        """Stable entrypoint for API callers using a DTO payload."""
        context = request.context.copy() if isinstance(request.context, dict) else {}
        if request.messages and "messages" not in context:
            context["messages"] = request.messages
        if request.system_prompt:
            context["system_instructions"] = request.system_prompt

        pipeline_request = PipelineRequest(
            prompt=self._resolve_prompt(request.messages),
            context=context,
        )
            payload = invoke_provider_or_raise(self._provider, pipeline_request)
            meta = payload["meta"]

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
    def _resolve_prompt(messages: list[dict]) -> str:
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "").lower() != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return ""

    def run_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> dict:
        """Compatibility shim that forwards legacy calls to `run(...)`."""
        dto = AIPipelineRequest(
            messages=[{"role": "user", "content": prompt}] if prompt else [],
            system_prompt=(context or {}).get("system_instructions"),
            context=context or {},
            chat_id=metadata.get("chat_id"),
            initiated_by=metadata.get("initiated_by"),
            class_id=metadata.get("class_id"),
            user_id=metadata.get("user_id"),
            rag=metadata.get("rag"),
            request_id=metadata.get("request_id"),
        )
        return self.run(dto)

    def list_available_models(self) -> dict[str, Any]:
        """Return provider/model inventory from configured local sources."""

        inventory_service = ModelInventoryService(
            ModelInventoryConfig(
                provider=self.config.provider,
                model_name=self.config.model_name,
                ollama_endpoint=self.config.ollama_endpoint,
                live_endpoint=self.config.live_endpoint,
                ollama_model_id=self.config.ollama_model_id,
                huggingface_model_id=self.config.huggingface_model_id,
                huggingface_cache_dir=self.config.huggingface_cache_dir,
                timeout_seconds=self.config.timeout_seconds,
            )
        )
        return inventory_service.list_available_models()

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
