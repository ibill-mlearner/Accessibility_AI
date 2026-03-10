from __future__ import annotations
import logging, time
from dataclasses import dataclass
from typing import Any

from .interfaces import (
    AIProviderFactoryInterface,
    AIProviderInterface,
    ModelInventoryServiceFactoryInterface,
)

from .exceptions import AIPipelineUpstreamError, invoke_provider_or_raise
from .model_inventory import ModelInventoryConfig, ModelInventoryService
from .providers import AIProvider, create_provider, normalize_provider_name
from .types import AIPipelineRequest

_ASSISTANT_TEXT_KEYS = ("assistant_text", "result", "answer", "response_text", "response", "output", "text")
logger = logging.getLogger(__name__)

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
    huggingface_allow_download: bool = False
    enable_ollama_fallback_on_hf_local_only_error: bool = True
    max_new_tokens: int = 256
    temperature: float = 0.1


class AIPipelineService:
    def __init__(
        self, 
        config: AIPipelineConfig,
        provider: AIProviderInterface | None = None,
        provider_factory: AIProviderFactoryInterface | None = None,
        inventory_service_factory: ModelInventoryServiceFactoryInterface | None = None,
    ) -> None:

        self.config = config
        self._provider_factory = provider_factory or create_provider
        self._inventory_service_factory = inventory_service_factory or ModelInventoryService
        self._provider = provider or self._provider_factory(
            provider=config.provider,
            model_name=config.model_name,
            mock_resource_path=config.mock_resource_path,
            live_endpoint=config.live_endpoint,
            ollama_endpoint=config.ollama_endpoint,
            ollama_model_id=config.ollama_model_id,
            ollama_options=config.ollama_options,
            timeout_seconds=config.timeout_seconds,
            huggingface_model_id=config.huggingface_model_id,
            huggingface_cache_dir=config.huggingface_cache_dir,
            huggingface_allow_download=config.huggingface_allow_download,
            enable_ollama_fallback_on_hf_local_only_error=config.enable_ollama_fallback_on_hf_local_only_error,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature
        )

        self._provider_cache: dict[tuple[str, str], AIProviderInterface] = {}
        default_key = (
            normalize_provider_name(self.config.provider),
            # self._resolve_prompt(self.config.provider),
            self._resolve_model_id_for_provider(self.config.provider)
        )
        if all(default_key):
            self._provider_cache[default_key] = self._provider

    def _resolve_model_id_for_provider(self, provider: str) -> str:
        selected = normalize_provider_name(provider)
        if selected == 'ollama':
            return str(
                self.config.ollama_model_id
                or self.config.model_name
                or self.config.huggingface_model_id
                or ""
            ).strip()
        if selected == "huggingface":
            return str(
                self.config.huggingface_model_id
                or self.config.model_name
                or ""
            ).strip()
        return str(self.config.model_name or "").strip()
    def _resolve_runtime_selection(
            self,
            context: dict[str, Any]
    ) -> tuple[str, str] | None:
        runtime_selection = context.get("runtime_model_selection")
        if not isinstance(runtime_selection, dict):
            return None

        provider = normalize_provider_name(runtime_selection.get("provider"))
        model_id = str(runtime_selection.get('model_id') or '').strip()
        if not provider or not model_id:
            return None

        return provider, model_id

    def _get_or_create_provider(
            self,
            provider: str,
            model_id: str
    ):
        key = (normalize_provider_name(provider), (model_id or '').strip())
        if key in self._provider_cache:
            return self._provider_cache[key]

        selected_provider, selected_mdoel_id = key
        provider_instance = self._provider_factory(
            provider=selected_provider,
            model_name=selected_mdoel_id or self.config.model_name,
            mock_resource_path=self.config.mock_resource_path,
            live_endpoint=self.config.live_endpoint,
            ollama_endpoint=self.config.ollama_endpoint,
            ollama_model_id=selected_mdoel_id if selected_provider == 'ollama' else self.config.ollama_model_id,
            ollama_options=self.config.ollama_options,
            timeout_seconds=self.config.timeout_seconds,
            huggingface_model_id=selected_mdoel_id if selected_provider == 'huggingface' else self.config.huggingface_model_id,
            huggingface_cache_dir=self.config.huggingface_cache_dir,
            huggingface_allow_download=self.config.huggingface_allow_download,
            enable_ollama_fallback_on_hf_local_only_error=self.config.enable_ollama_fallback_on_hf_local_only_error,
            max_new_tokens=self.config.max_new_tokens,
            temperature=self.config.temperature
        )
        self._provider_cache[key] = provider_instance
        return provider_instance

    @staticmethod
    def _is_hf_local_only_bootstrap_error(exc: AIPipelineUpstreamError) -> bool:
        message = str(exc).lower()
        if "dynamic download is disabled in local-only mode" in message:
            return True

        details = exc.details if isinstance(exc.details, dict) else {}
        exc_name = str(details.get("exception") or "").lower()
        source = str(details.get("source") or "").lower()
        return (
            exc_name == "runtimeerror"
            and source == "provider_runtime"
            and "local-only mode" in message
            and "ai_huggingface_cache_dir" in message
        )

    def _resolve_ollama_fallback_target(self) -> tuple[AIProviderInterface, str] | None:
        model_id = self._resolve_model_id_for_provider("ollama")
        if not model_id:
            return None

        endpoint = str(self.config.ollama_endpoint or self.config.live_endpoint or "").strip()
        if not endpoint:
            return None

        return self._get_or_create_provider("ollama", model_id), model_id

    def _fallback_provider_if_eligible(
        self,
        exc: AIPipelineUpstreamError,
        *,
        selected_provider: str,
        request_id: str,
    ) -> tuple[AIProviderInterface, str, dict[str, str]] | None:
        if not self.config.enable_ollama_fallback_on_hf_local_only_error:
            return None
        if normalize_provider_name(selected_provider) != "huggingface":
            return None
        if not self._is_hf_local_only_bootstrap_error(exc):
            return None

        fallback_target = self._resolve_ollama_fallback_target()
        if fallback_target is None:
            logger.warning(
                "ai_pipeline.run.fallback.unavailable request_id=%s reason=%s",
                request_id,
                "ollama_not_configured",
            )
            return None

        provider_instance, fallback_model = fallback_target
        fallback_meta = {
            "fallback_from": "huggingface",
            "fallback_to": "ollama",
            "fallback_reason": "huggingface_local_only_bootstrap_error",
        }
        logger.info(
            "ai_pipeline.run.fallback.apply request_id=%s from=%s to=%s model=%s reason=%s",
            request_id,
            "huggingface",
            "ollama",
            fallback_model,
            fallback_meta["fallback_reason"],
        )
        return provider_instance, fallback_model, fallback_meta

    def run(
        self, 
        request: AIPipelineRequest
    ) -> dict[str, Any]:

        prompt = self._resolve_prompt(request)
        request_id = str(request.request_id) if request.request_id is not None else "n/a"
        context = request.context.copy() if isinstance(request.context, dict) else {}
        runtime_selection = self._resolve_runtime_selection(context)
        provider_instance = self._provider
        selected_provider = normalize_provider_name(self.config.provider)
        selected_model = self._resolve_model_id_for_provider(selected_provider)

        if runtime_selection is not None:
            override_provider, override_model_id = runtime_selection
            try:
                provider_instance = self._get_or_create_provider(override_provider, override_model_id)
                selected_provider = override_provider
                selected_model = override_model_id
            except ValueError:
                logger.warning(
                    "ai.pipeline.run.runtime_selection_invalid requst_id=%s provier=%s model=%s",
                    request_id,
                    override_provider,
                    override_model_id,
                )

        logger.debug(
            "ai_pipeline.run.start request_id=%s provider=%s model=%s timeout_seconds=%s prompt_len=%s messages_count=%s prompt_preview=%r",
            request_id,
            selected_provider,
            selected_model,
            self.config.timeout_seconds,
            len(prompt),
            len(request.messages) if isinstance(request.messages, list) else 0,
            prompt[:200],
        )

        # context = request.context.copy() if isinstance(request.context, dict) else {}

        if request.request_id and "request_id" not in context:
            context["request_id"] = request.request_id
        if request.messages and "messages" not in context:
            context["messages"] = request.messages
        if request.system_prompt:
            context["system_instructions"] = request.system_prompt
        invoke_start_time = time.time()
        logger.debug(
            "ai_pipeline.run.invoke provider=%s endpoint=%s model=%s invoke_called=%s invoke_start_time=%s",
            selected_provider,
            self.config.live_endpoint or self.config.ollama_endpoint or "n/a",
            selected_model,
            True,
            invoke_start_time
        )
        fallback_meta: dict[str, str] = {}
        try:
            payload = invoke_provider_or_raise(provider_instance, prompt, context)
        except AIPipelineUpstreamError as exc:
            fallback = self._fallback_provider_if_eligible(
                exc,
                selected_provider=selected_provider,
                request_id=request_id,
            )
            if fallback is None:
                raise
            provider_instance, selected_model, fallback_meta = fallback
            selected_provider = "ollama"
            payload = invoke_provider_or_raise(provider_instance, prompt, context)

        logger.debug(
            "ai_pipeline.run.invoke.completed provider=%s return_value=%s duration_ms=%s",
            selected_provider,
            payload is None,
            round((time.time() - invoke_start_time) * 1000, 2)
        )

        assistant_text = next((str(payload[k]) for k in _ASSISTANT_TEXT_KEYS if payload.get(k) is not None), "")
        confidence = float(payload["confidence"]) if isinstance(payload.get("confidence"), (int, float)) else None
        notes_raw = payload.get("notes")
        notes = [str(n) for n in notes_raw] if isinstance(notes_raw, list) else ([notes_raw.strip()] if isinstance(notes_raw, str) and notes_raw.strip() else [])
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        result = {
            "assistant_text": assistant_text,
            "confidence": confidence,
            "notes": notes,
            "meta": {
                **meta,
                "provider": meta.get("provider") or selected_provider,
                "model": meta.get("model") or meta.get("model_id") or selected_model,
                "pipeline": "app.services.ai_pipeline",
                "selected_provider": selected_provider,
                "selected_model_id": selected_model,
                **fallback_meta,
            },
        }

        if not assistant_text:
            logger.warning(
                "ai_pipeline.run.empty_assistant request_id=%s provider=%s model=%s notes_count=%s",
                request_id,
                selected_provider,
                selected_model,
                len(notes)

            )

        logger.debug(
            "ai_pipeline.run.end request_id=%s provider=%s model=%s assistant_text_len=%s notes_count=%s assistant_text_preview=%r",
            request_id,
            self.config.provider,
            self.config.model_name,
            len(assistant_text),
            len(notes),
            assistant_text[:200]
        )

        return result

    @staticmethod
    def _resolve_prompt(request: AIPipelineRequest) -> str:
        explicit_prompt = request.prompt if isinstance(request.prompt, str) else ""
        prompt = explicit_prompt.strip()
        if prompt:
            return prompt

        for message in reversed(
            request.messages if isinstance(request.messages, list) else []
        ):
            if (
                isinstance(message, dict) 
                and str(message.get("role") or "").lower() == "user" 
                and isinstance(message.get("content"), str) 
                and message["content"].strip()
            ):
                return message["content"].strip()
        return ""

    def run_interaction(
        self, 
        prompt: str, 
        context: dict[str, Any] | None = None, 
        **metadata: Any
    ) -> dict[str, Any]:
    
        return self.run(
            AIPipelineRequest(
                prompt=prompt,
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

    def provider_health(self) -> dict[str, Any]:

        statuses: dict[str, Any] = {}

        defaults = {
            "ollama": self.config.ollama_model_id or self.config.model_name,
            "huggingface": self.config.huggingface_model_id or self.config.model_name,
        }
        for provider_name in ("ollama", "huggingface"):
            model_id = str(defaults.get(provider_name) or "").strip()

            if not model_id:
                statuses[provider_name] = {"ok": False, "status": "not_configured"}
                continue

            try:
                provider = self._get_or_create_provider(provider_name, model_id)
                statuses[provider_name] = provider.health()

            except Exception as exc:
                statuses[provider_name] = {
                    "ok": False,
                    "status": "health_check_failed",
                    "error": str(exc),
                    "model_id": model_id,
                }
        return statuses

    def list_available_models(self) -> dict[str, Any]:
        return self._inventory_service_factory(
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
