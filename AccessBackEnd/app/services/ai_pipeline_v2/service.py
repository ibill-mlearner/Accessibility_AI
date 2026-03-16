from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .interfaces import AIProviderFactoryInterface, AIProviderInterface
from .providers import map_exception, normalize_backend_response, normalize_provider_name
from .types import ASSISTANT_TEXT_KEYS, AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError


class AIPipelineService:
    def __init__(
        self,
        config: AIPipelineConfig,
        provider: AIProviderInterface | None = None,
        provider_factory: AIProviderFactoryInterface | None = None,
    ) -> None:
        self.config = config
        self._provider_factory = provider_factory
        default_provider = normalize_provider_name(config.provider)
        default_model = self._resolve_model_id(default_provider)
        self._backends: dict[tuple[str, str], AIProviderInterface] = {}
        if provider is not None:
            self._backends[(default_provider, default_model)] = provider
        self._inventory_cache: tuple[float, dict[str, Any]] | None = None

    def _resolve_model_id(self, provider: str) -> str:
        if provider == "ollama":
            return str(self.config.ollama_model_id or self.config.model_name or self.config.huggingface_model_id or "").strip()
        if provider == "huggingface":
            return str(self.config.huggingface_model_id or self.config.model_name or "").strip()
        return str(self.config.model_name or "").strip()

    def _select_runtime(self, context: dict[str, Any]) -> tuple[str, str]:
        runtime = context.get("runtime_model_selection")
        if isinstance(runtime, dict):
            provider = normalize_provider_name(runtime.get("provider"))
            model = str(runtime.get("model_id") or "").strip()
            if provider and model:
                return provider, model
        provider = normalize_provider_name(self.config.provider)
        return provider, self._resolve_model_id(provider)

    def _get_backend(self, provider: str, model_id: str) -> AIProviderInterface:
        key = (provider, model_id)
        if key in self._backends:
            return self._backends[key]
        if self._provider_factory is None:
            raise ValueError("provider_factory is required to create providers")
        instance = self._provider_factory(self.config, provider=provider, model_id=model_id)
        self._backends[key] = instance
        return instance

    @staticmethod
    def _resolve_prompt(request: AIPipelineRequest) -> str:
        explicit_prompt = request.prompt if isinstance(request.prompt, str) else ""
        prompt = explicit_prompt.strip()
        if prompt:
            return prompt
        for message in reversed(request.messages if isinstance(request.messages, list) else []):
            if isinstance(message, dict) and str(message.get("role") or "").lower() == "user" and isinstance(message.get("content"), str) and message["content"].strip():
                return message["content"].strip()
        return ""

    @staticmethod
    def _extract_assistant_text(payload: dict[str, Any]) -> str:
        for key in ASSISTANT_TEXT_KEYS:
            if payload.get(key) is not None:
                return str(payload.get(key))
        return ""

    @staticmethod
    def _is_hf_local_only_bootstrap_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "local-only mode" in message and "huggingface" in message

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        prompt = self._resolve_prompt(request)
        context = request.context.copy() if isinstance(request.context, dict) else {}
        if request.request_id and "request_id" not in context:
            context["request_id"] = request.request_id
        if request.messages and "messages" not in context:
            context["messages"] = request.messages
        if request.system_prompt:
            context["system_instructions"] = request.system_prompt

        provider_name, model_id = self._select_runtime(context)
        backend = self._get_backend(provider_name, model_id)

        invoke_start = time.time()
        fallback_meta: dict[str, str] = {}
        try:
            payload = backend.generate(prompt, str(context.get("system_instructions") or ""), context) if hasattr(backend, "generate") else backend.invoke(prompt, context)
        except Exception as exc:  # noqa: BLE001
            mapped = map_exception(exc)
            should_fallback = (
                provider_name == "huggingface"
                and bool(self.config.enable_ollama_fallback_on_hf_local_only_error)
                and self._is_hf_local_only_bootstrap_error(mapped)
            )
            if should_fallback:
                provider_name = "ollama"
                model_id = self._resolve_model_id("ollama")
                backend = self._get_backend(provider_name, model_id)
                payload = backend.generate(prompt, str(context.get("system_instructions") or ""), context) if hasattr(backend, "generate") else backend.invoke(prompt, context)
                fallback_meta = {
                    "fallback_from": "huggingface",
                    "fallback_to": "ollama",
                    "fallback_reason": "huggingface_local_only_bootstrap_error",
                }
            else:
                details = getattr(mapped, "details", {}) if isinstance(getattr(mapped, "details", {}), dict) else {}
                raise AIPipelineUpstreamError(
                    f"Selected provider '{provider_name}' is unavailable for model '{model_id}'. {mapped}",
                    details={
                        **details,
                        "error_code": "provider_unavailable",
                        "provider": provider_name,
                        "model_id": model_id,
                        "selected_provider": provider_name,
                        "selected_model_id": model_id,
                    },
                ) from exc

        _ = invoke_start  # keep timing hook available for future logging
        payload = normalize_backend_response(payload)
        assistant_text = self._extract_assistant_text(payload)
        confidence = float(payload["confidence"]) if isinstance(payload.get("confidence"), (float, int)) else None
        notes_raw = payload.get("notes")
        notes = [str(n) for n in notes_raw] if isinstance(notes_raw, list) else ([notes_raw.strip()] if isinstance(notes_raw, str) and notes_raw.strip() else [])
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        return {
            "assistant_text": assistant_text,
            "confidence": confidence,
            "notes": notes,
            "meta": {
                **meta,
                "provider": meta.get("provider") or provider_name,
                "model": meta.get("model") or meta.get("model_id") or model_id,
                "pipeline": "app.services.ai_pipeline_v2",
                "selected_provider": provider_name,
                "selected_model_id": model_id,
                **fallback_meta,
            },
        }

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **metadata: Any) -> dict[str, Any]:
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
        for provider_name in ("ollama", "huggingface"):
            model_id = self._resolve_model_id(provider_name)
            if not model_id:
                statuses[provider_name] = {"ok": False, "status": "not_configured"}
                continue
            try:
                statuses[provider_name] = self._get_backend(provider_name, model_id).health()
            except Exception as exc:  # noqa: BLE001
                statuses[provider_name] = {"ok": False, "status": "health_check_failed", "error": str(exc), "model_id": model_id}
        return statuses

    def list_available_models(self) -> dict[str, Any]:
        now = time.time()
        ttl = max(int(self.config.inventory_cache_ttl_seconds), 1)
        if self._inventory_cache and now - self._inventory_cache[0] < ttl:
            cached_payload = self._inventory_cache[1]
            meta = cached_payload.get("meta") if isinstance(cached_payload.get("meta"), dict) else {}
            cached_payload["meta"] = {**meta, "cache_hit": True, "cache_ttl_seconds": ttl}
            return cached_payload

        warnings: list[dict[str, Any]] = []
        provider_timings: dict[str, float] = {}
        ollama_models: list[dict[str, Any]] = []
        hf_models: list[dict[str, Any]] = []

        inventory_start = time.perf_counter()

        def _fetch_inventory(provider_name: str, model_id: str) -> tuple[str, list[dict[str, Any]], float]:
            provider_start = time.perf_counter()
            models = self._get_backend(provider_name, model_id).inventory()
            return provider_name, models, round((time.perf_counter() - provider_start) * 1000, 2)

        futures = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            for provider_name in ("ollama", "huggingface"):
                model_id = self._resolve_model_id(provider_name)
                if not model_id:
                    continue
                futures.append(executor.submit(_fetch_inventory, provider_name, model_id))

            for future in as_completed(futures):
                try:
                    provider_name, models, duration_ms = future.result()
                    provider_timings[provider_name] = duration_ms
                    if provider_name == "ollama":
                        ollama_models = models
                    else:
                        hf_models = models
                except Exception as exc:  # noqa: BLE001
                    warnings.append({"source": "inventory", "message": str(exc)})

        payload = {
            "provider_defaults": {
                "provider": self.config.provider,
                "model_name": self.config.model_name,
                "ollama_model_id": self.config.ollama_model_id,
                "huggingface_model_id": self.config.huggingface_model_id,
            },
            "ollama": {"models": ollama_models, "count": len(ollama_models)},
            "huggingface_local": {"models": hf_models, "count": len(hf_models)},
            "meta": {
                "pipeline": "app.services.ai_pipeline_v2",
                "warnings": warnings,
                "timings_ms": {
                    "total": round((time.perf_counter() - inventory_start) * 1000, 2),
                    "providers": provider_timings,
                },
                "cache_hit": False,
                "cache_ttl_seconds": ttl,
            },
        }
        self._inventory_cache = (now, payload)
        return payload
