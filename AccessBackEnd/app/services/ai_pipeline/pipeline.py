from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import invoke_provider_or_raise
from .model_inventory import ModelInventoryConfig, ModelInventoryService
from .providers import AIProvider, HTTPEndpointProvider, HuggingFaceLangChainProvider, MockJSONProvider, OllamaProvider
from .types import AIPipelineRequest

_ASSISTANT_TEXT_KEYS = ("assistant_text", "result", "answer", "response_text", "response", "output", "text")


@dataclass(slots=True)
class AIPipelineConfig:
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
    def __init__(self, config: AIPipelineConfig) -> None:
        self.config = config
        self._provider = self._build_provider(config)

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        context = request.context.copy() if isinstance(request.context, dict) else {}
        if request.messages and "messages" not in context:
            context["messages"] = request.messages
        if request.system_prompt:
            context["system_instructions"] = request.system_prompt
        payload = invoke_provider_or_raise(self._provider, self._resolve_prompt(request.messages), context)

        assistant_text = next((str(payload[k]) for k in _ASSISTANT_TEXT_KEYS if payload.get(k) is not None), "")
        confidence = float(payload["confidence"]) if isinstance(payload.get("confidence"), (int, float)) else None
        notes_raw = payload.get("notes")
        notes = [str(n) for n in notes_raw] if isinstance(notes_raw, list) else ([notes_raw.strip()] if isinstance(notes_raw, str) and notes_raw.strip() else [])
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        return {
            "assistant_text": assistant_text,
            "confidence": confidence,
            "notes": notes,
            "meta": {
                **meta,
                "model": meta.get("model") or meta.get("model_id") or self.config.model_name,
                "pipeline": "app.services.ai_pipeline",
                "selected_provider": self.config.provider,
            },
        }

    @staticmethod
    def _resolve_prompt(messages: list[dict]) -> str:
        for message in reversed(messages):
            if isinstance(message, dict) and str(message.get("role") or "").lower() == "user" and isinstance(message.get("content"), str) and message["content"].strip():
                return message["content"].strip()
        return ""

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **metadata: Any) -> dict[str, Any]:
        return self.run(
            AIPipelineRequest(
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
        )

    def list_available_models(self) -> dict[str, Any]:
        return ModelInventoryService(
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
        ).list_available_models()

    def _build_provider(self, config: AIPipelineConfig) -> AIProvider:
        provider = (config.provider or "ollama").strip().lower()
        if provider in {"mock", "mock_json", "json"}:
            return MockJSONProvider(mock_resource_path=config.mock_resource_path)
        if provider in {"ollama", "ollama_local"}:
            return OllamaProvider(endpoint=config.ollama_endpoint or config.live_endpoint, model_id=config.ollama_model_id or config.model_name or config.huggingface_model_id, options=config.ollama_options, timeout_seconds=config.timeout_seconds)
        if provider in {"live", "live_agent", "http"}:
            return HTTPEndpointProvider(endpoint=config.live_endpoint, model_name=config.model_name, timeout_seconds=config.timeout_seconds)
        if provider in {"hf", "huggingface", "langchain_hf"}:
            return HuggingFaceLangChainProvider(model_id=config.huggingface_model_id, cache_dir=config.huggingface_cache_dir, max_new_tokens=config.max_new_tokens, temperature=config.temperature)
        raise ValueError(f"Unsupported AI provider: {config.provider}")
