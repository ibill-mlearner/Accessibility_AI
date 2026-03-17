from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from transformers import pipeline

from .types import AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError


class AIPipelineService:
    """Single-class interface for prompt/message generation via Hugging Face pipeline."""

    def __init__(self, config: AIPipelineConfig | None = None) -> None:
        self.config = config or AIPipelineConfig()
        dtype = torch.bfloat16 if self.config.torch_dtype == "bfloat16" else torch.float32
        self._pipe = pipeline(
            "text-generation",
            model=self.config.model_id,
            torch_dtype=dtype,
            device_map=self.config.device_map,
        )
        self._save_model_config()

    def _save_model_config(self) -> None:
        path = Path(self.config.config_log_path)
        path.write_text(f"model_id={self.config.model_id}\n", encoding="utf-8")

    @staticmethod
    def _resolve_messages(request: AIPipelineRequest) -> list[dict[str, str]]:
        if request.messages:
            return [
                {
                    "role": str(message.get("role") or "user"),
                    "content": str(message.get("content") or ""),
                }
                for message in request.messages
                if isinstance(message, dict)
            ]
        prompt = (request.prompt or "").strip()
        if not prompt:
            return []
        role = str((request.context or {}).get("role") or "user")
        return [{"role": role, "content": prompt}]

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        messages = self._resolve_messages(request)
        if not messages:
            raise AIPipelineUpstreamError("Prompt or messages are required")
        settings = request.context if isinstance(request.context, dict) else {}
        max_new_tokens = int(settings.get("max_new_tokens", self.config.max_new_tokens))
        temperature = float(settings.get("temperature", self.config.temperature))
        try:
            outputs = self._pipe(messages, max_new_tokens=max_new_tokens, temperature=temperature)
            assistant_text = outputs[0]["generated_text"][-1]
            return {
                "assistant_text": assistant_text,
                "meta": {
                    "model_id": self.config.model_id,
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "role": messages[-1].get("role"),
                    "message": messages[-1].get("content"),
                    "metadata": settings.get("metadata", {}),
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
        return {"status": "ok", "model_id": self.config.model_id}

    def list_available_models(self) -> dict[str, Any]:
        return {"models": [{"provider": "huggingface", "id": self.config.model_id}]}


AIPipeline = AIPipelineService
