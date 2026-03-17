from __future__ import annotations

from datetime import datetime, timezone
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
        self._pipe_by_model: dict[str, Any] = {}
        self._save_model_config()

    def _save_model_config(self) -> None:
        Path(self.config.config_log_path).write_text(f"model_id={self.config.model_id}\n", encoding="utf-8")


    def _resolve_runtime_model_id(self, request: AIPipelineRequest) -> str:
        context = request.context if isinstance(request.context, dict) else {}
        runtime = context.get("runtime_model_selection") if isinstance(context.get("runtime_model_selection"), dict) else {}
        selected_model_id = str(runtime.get("model_id") or "").strip()
        return selected_model_id or self.config.model_id

    def _ensure_pipe(self, model_id: str):
        existing = self._pipe_by_model.get(model_id)
        if existing is not None:
            return existing
        if self._runtime_client_factory is not None:
            pipe = self._runtime_client_factory(self.config)
            self._pipe_by_model[model_id] = pipe
            return pipe
        dtype = torch.bfloat16 if self.config.torch_dtype == "bfloat16" else torch.float32
        pipe = pipeline(
            "text-generation",
            model=model_id,
            torch_dtype=dtype,
            device_map=self.config.device_map,
        )
        self._pipe_by_model[model_id] = pipe
        return pipe

    @staticmethod
    def _has_hf_artifacts(path: Path) -> bool:
        if not (path / "config.json").exists():
            return False
        marker_files = (
            "tokenizer.json",
            "tokenizer_config.json",
            "model.safetensors",
            "model.safetensors.index.json",
            "pytorch_model.bin",
            "pytorch_model.bin.index.json",
        )
        return any((path / marker).exists() for marker in marker_files)

    def _discover_local_models(self) -> list[dict[str, Any]]:
        roots = [Path(__file__).resolve().parents[3] / "instance" / "models"]
        configured = Path(self.config.model_id).expanduser()
        if configured.exists() and configured.is_dir():
            roots.append(configured.parent)

        models: list[dict[str, Any]] = []
        seen: set[str] = set()
        for root in roots:
            if not root.exists() or not root.is_dir():
                continue
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                if not (child.name.lower().startswith("models--") or self._has_hf_artifacts(child)):
                    continue
                resolved = child.resolve().as_posix()
                if resolved in seen:
                    continue
                seen.add(resolved)
                stat = child.stat()
                models.append(
                    {
                        "id": child.name,
                        "source": "huggingface_local",
                        "path": resolved,
                        "size": None,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    }
                )
        return sorted(models, key=lambda item: item["id"])

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
        selected_model_id = self._resolve_runtime_model_id(request)

        try:
            outputs = self._ensure_pipe(selected_model_id)(messages, max_new_tokens=max_new_tokens)
            assistant_text = self._extract_last_generated_message(outputs)
            return {
                "assistant_text": assistant_text,
                "meta": {
                    "provider": "huggingface",
                    "model_id": selected_model_id,
                    "selected_provider": "huggingface",
                    "selected_model_id": selected_model_id,
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
        local_models = self._discover_local_models()
        return {
            "model_defaults": {
                "provider": "huggingface",
                "model_name": self.config.model_id,
                "huggingface_model_id": self.config.model_id,
            },
            "huggingface_local": {"models": local_models, "count": len(local_models)},
            "local": {"models": local_models, "count": len(local_models)},
            "models": [{"provider": "huggingface", "id": model["id"]} for model in local_models],
        }


AIPipeline = AIPipelineService
