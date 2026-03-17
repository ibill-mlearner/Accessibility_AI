from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from transformers import pipeline

from .types import AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError


class AIPipelineService:
    """HuggingFace transformers pipeline service for chat-style text generation."""

    def __init__(
        self,
        config: AIPipelineConfig | None = None,
        runtime_client: Any | None = None,
        runtime_client_factory: Any | None = None,
        provider: Any | None = None,
        provider_factory: Any | None = None,
        inventory_service_factory: Any | None = None,
    ) -> None:
        _ = runtime_client, provider, inventory_service_factory
        self.config = config or AIPipelineConfig()
        self._runtime_client_factory = runtime_client_factory or provider_factory
        self._pipe = None
        self._save_model_config()

    def _save_model_config(self) -> None:
        Path(self.config.config_log_path).write_text(f"model_id={self.config.model_id}\n", encoding="utf-8")


    def _ensure_pipe(self):
        if self._pipe is not None:
            return self._pipe
        if self._runtime_client_factory is not None:
            self._pipe = self._runtime_client_factory(self.config)
            return self._pipe
        dtype = torch.bfloat16 if self.config.torch_dtype == "bfloat16" else torch.float32
        self._pipe = pipeline(
            "text-generation",
            model=self.config.model_id,
            torch_dtype=dtype,
            device_map=self.config.device_map,
        )
        return self._pipe

    @staticmethod
    def _resolve_messages(request: AIPipelineRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": str(request.system_prompt)})

        if request.messages:
            messages.extend(
                [
                    {
                        "role": str(message.get("role") or "user"),
                        "content": str(message.get("content") or ""),
                    }
                    for message in request.messages
                    if isinstance(message, dict)
                ]
            )
            return messages

        prompt = (request.prompt or "").strip()
        if prompt:
            messages.append({"role": str((request.context or {}).get("role") or "user"), "content": prompt})
        return messages

    @staticmethod
    def _extract_last_generated_message(outputs: Any) -> str:
        if not isinstance(outputs, list) or not outputs:
            return ""
        first = outputs[0]
        if not isinstance(first, dict):
            return ""
        generated = first.get("generated_text")
        if isinstance(generated, list) and generated:
            last = generated[-1]
            if isinstance(last, dict):
                return str(last.get("content") or "")
            return str(last)
        return str(generated or "")

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        messages = self._resolve_messages(request)
        if not messages:
            raise AIPipelineUpstreamError("Prompt or messages are required")

        settings = request.context if isinstance(request.context, dict) else {}
        max_new_tokens = int(settings.get("max_new_tokens", self.config.max_new_tokens))

        try:
            outputs = self._ensure_pipe()(messages, max_new_tokens=max_new_tokens)
            assistant_text = self._extract_last_generated_message(outputs)
            return {
                "assistant_text": assistant_text,
                "meta": {
                    "provider": "huggingface",
                    "model_id": self.config.model_id,
                    "selected_provider": "huggingface",
                    "selected_model_id": self.config.model_id,
                    "max_new_tokens": max_new_tokens,
                },
            }
        except Exception as exc:  # noqa: BLE001
            raise AIPipelineUpstreamError("Model invocation failed", details={"error": str(exc)}) from exc

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **metadata: Any) -> dict[str, Any]:
        merged_context = dict(context or {})
        if metadata:
            merged_context["metadata"] = metadata
        return self.run(AIPipelineRequest(prompt=prompt, context=merged_context))

    def generate_text(self, text: str, model_name: str) -> dict[str, Any]:
        _ = model_name
        return self.run(AIPipelineRequest(prompt=text))

    def provider_health(self) -> dict[str, Any]:
        return {"status": "ok", "provider": "huggingface", "model_id": self.config.model_id}

    def list_available_models(self) -> dict[str, Any]:
        return {
            "huggingface_local": {"models": [{"id": self.config.model_id}]},
            "models": [{"provider": "huggingface", "id": self.config.model_id}],
        }


AIPipeline = AIPipelineService
