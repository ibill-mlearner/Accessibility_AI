from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .interfaces import AIProviderFactoryInterface, AIProviderInterface
from .providers import HuggingFaceBackend, map_exception, normalize_backend_response
from .types import ASSISTANT_TEXT_KEYS, AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError


class AIPipelineService:
    def __init__(
        self,
        config: AIPipelineConfig | None = None,
        runtime_client: AIProviderInterface | None = None,
        runtime_client_factory: AIProviderFactoryInterface | None = None,
        provider: AIProviderInterface | None = None,
        provider_factory: AIProviderFactoryInterface | None = None,
    ) -> None:
        self.config = config or AIPipelineConfig(model_name=str(os.getenv("AI_MODEL_NAME") or "").strip())
        self._runtime_client_factory = runtime_client_factory or provider_factory
        selected_client = runtime_client or provider
        self._runtime_clients: dict[str, AIProviderInterface] = {}
        default_model = self._resolve_model_id()
        if selected_client is not None:
            self._runtime_clients[default_model] = selected_client
        self._inventory_cache: tuple[float, dict[str, Any]] | None = None

    def _resolve_model_id(self) -> str:
        return str(self.config.huggingface_model_id or self.config.model_name or "").strip()

    def _select_model_id(self, context: dict[str, Any]) -> str:
        runtime = context.get("runtime_model_selection")
        if isinstance(runtime, dict):
            model = str(runtime.get("model_id") or "").strip()
            if model:
                return model
        return self._resolve_model_id()

    def _get_runtime_client(self, model_id: str) -> AIProviderInterface:
        if model_id in self._runtime_clients:
            return self._runtime_clients[model_id]
        if self._runtime_client_factory is None:
            self._runtime_client_factory = lambda cfg, *, model_id: HuggingFaceBackend(config=cfg, model_id=model_id)
        instance = self._runtime_client_factory(self.config, model_id=model_id)
        self._runtime_clients[model_id] = instance
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

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        prompt = self._resolve_prompt(request)
        context = request.context.copy() if isinstance(request.context, dict) else {}
        if request.request_id and "request_id" not in context:
            context["request_id"] = request.request_id
        if request.messages and "messages" not in context:
            context["messages"] = request.messages
        if request.system_prompt:
            context["system_instructions"] = request.system_prompt

        model_id = self._select_model_id(context)
        runtime_client = self._get_runtime_client(model_id)

        invoke_start = time.time()
        try:
            payload = runtime_client.generate(prompt, str(context.get("system_instructions") or ""), context) if hasattr(runtime_client, "generate") else runtime_client.invoke(prompt, context)
        except Exception as exc:  # noqa: BLE001
            mapped = map_exception(exc)
            details = getattr(mapped, "details", {}) if isinstance(getattr(mapped, "details", {}), dict) else {}
            raise AIPipelineUpstreamError(
                "There was a problem with the model contact the administrator.",
                details={
                    **details,
                    "error_code": "runtime_unavailable",
                    "model_id": model_id,
                    "selected_model_id": model_id,
                },
            ) from exc

        _ = invoke_start
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
                "model": meta.get("model") or meta.get("model_id") or model_id,
                "pipeline": "app.services.ai_pipeline_v2",
                "selected_model_id": model_id,
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

    def generate_text(self, text: str, model_name: str) -> dict[str, Any]:
        context = {"runtime_model_selection": {"model_id": str(model_name or "").strip()}}
        request = AIPipelineRequest(prompt=str(text or ""), system_prompt="", context=context)
        return self.run(request)

    def provider_health(self) -> dict[str, Any]:
        statuses: dict[str, Any] = {}
        model_id = self._resolve_model_id()
        if not model_id:
            statuses["runtime"] = {"ok": False, "status": "not_configured"}
            return statuses
        try:
            statuses["runtime"] = self._get_runtime_client(model_id).health()
        except Exception as exc:  # noqa: BLE001
            statuses["runtime"] = {"ok": False, "status": "health_check_failed", "error": str(exc), "model_id": model_id}
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
        timings: dict[str, float] = {}
        models: list[dict[str, Any]] = []

        inventory_start = time.perf_counter()

        def _fetch_inventory(model_id: str) -> tuple[list[dict[str, Any]], float]:
            runtime_start = time.perf_counter()
            payload = self._get_runtime_client(model_id).inventory()
            return payload, round((time.perf_counter() - runtime_start) * 1000, 2)

        model_id = self._resolve_model_id()
        if model_id:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_fetch_inventory, model_id)
                try:
                    models, duration_ms = future.result()
                    timings["runtime"] = duration_ms
                except Exception as exc:  # noqa: BLE001
                    warnings.append({"source": "inventory", "message": str(exc)})

        local_bucket = {"models": models, "count": len(models)}
        payload = {
            "model_defaults": {
                "model_name": self.config.model_name,
                "model_id": self.config.huggingface_model_id,
            },
            # Canonical inventory bucket consumed by model-selection paths.
            "huggingface_local": local_bucket,
            # Backward-compatible alias retained for existing clients.
            "local": local_bucket,
            "meta": {
                "pipeline": "app.services.ai_pipeline_v2",
                "warnings": warnings,
                "timings_ms": {
                    "total": round((time.perf_counter() - inventory_start) * 1000, 2),
                    "runtime": timings,
                },
                "cache_hit": False,
                "cache_ttl_seconds": ttl,
            },
        }
        self._inventory_cache = (now, payload)
        return payload


class AIPipeline(AIPipelineService):
    def __init__(self) -> None:
        super().__init__()

    def AIPipelineRequest(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.run_interaction(prompt=prompt, context=context or {})
