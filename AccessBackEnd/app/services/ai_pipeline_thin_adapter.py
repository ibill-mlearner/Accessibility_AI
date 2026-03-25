from __future__ import annotations

from typing import Any

from flask import current_app

from .ai_pipeline_contracts import AIPipelineRequest, AIPipelineUpstreamError


class AIPipelineThinAdapter:
    """Single thin adapter that maps app requests to the ai_pipeline module flow."""

    @staticmethod
    def _resolve_prompt(request: AIPipelineRequest) -> str:
        prompt = str(request.prompt or "").strip()
        if prompt:
            return prompt
        for message in reversed(request.messages if isinstance(request.messages, list) else []):
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "").strip().lower() != "user":
                continue
            content = str(message.get("content") or "").strip()
            if content:
                return content
        return ""

    @staticmethod
    def _runtime_inputs(request: AIPipelineRequest) -> tuple[str, str, bool, int]:
        context = request.context if isinstance(request.context, dict) else {}
        runtime = context.get("runtime_model_selection") if isinstance(context.get("runtime_model_selection"), dict) else {}

        model_name = str(runtime.get("model_id") or context.get("model_name") or current_app.config.get("AI_MODEL_NAME") or "HuggingFaceTB/SmolLM2-360M-Instruct").strip()
        system_content = str(request.system_prompt or context.get("system_content") or current_app.config.get("AI_SYSTEM_CONTENT") or "").strip()
        download_locally = bool(context.get("download_locally", current_app.config.get("AI_DOWNLOAD_LOCALLY", True)))
        max_new_tokens = int(context.get("max_new_tokens", current_app.config.get("AI_MAX_NEW_TOKENS", 256)))
        return model_name, system_content, download_locally, max_new_tokens

    @staticmethod
    def _run_pipeline_once(*, model_name: str, system_content: str, prompt_value: str, download_locally: bool, max_new_tokens: int) -> str:
        try:
            import ai_pipeline
        except Exception as exc:  # noqa: BLE001
            raise AIPipelineUpstreamError(
                "Thin pipeline module import failed",
                details={"error_code": "runtime_unavailable", "error": str(exc), "provider": "huggingface", "model_id": model_name},
            ) from exc

        try:
            pipeline = ai_pipeline.AIPipeline(
                model_name_value=model_name,
                system_content=system_content,
                prompt_value=prompt_value,
                download_locally=download_locally,
            )
            pipeline.model_loader.device_map = "auto"
            pipeline.model_loader.torch_dtype = "auto"

            model = pipeline.build_model()
            tokenizer = pipeline.build_tokenizer()
            text = pipeline.build_text(tokenizer=tokenizer)
            model_inputs = pipeline.build_model_inputs(tokenizer=tokenizer, text=text, model=model)
            raw_generated_ids = pipeline.build_raw_generated_ids(
                model=model,
                model_inputs=model_inputs,
                max_new_tokens=max_new_tokens,
            )
            generated_ids = pipeline.build_generated_ids(model_inputs=model_inputs, raw_generated_ids=raw_generated_ids)
            response = pipeline.build_response(tokenizer=tokenizer, generated_ids=generated_ids)
            return str(response or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise AIPipelineUpstreamError(
                "Model invocation failed",
                details={"error_code": "upstream_error", "error": str(exc), "provider": "huggingface", "model_id": model_name},
            ) from exc

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        prompt_value = self._resolve_prompt(request)
        if not prompt_value:
            raise AIPipelineUpstreamError("Prompt or messages are required")

        model_name, system_content, download_locally, max_new_tokens = self._runtime_inputs(request)
        assistant_text = self._run_pipeline_once(
            model_name=model_name,
            system_content=system_content,
            prompt_value=prompt_value,
            download_locally=download_locally,
            max_new_tokens=max_new_tokens,
        )

        return {
            "assistant_text": assistant_text,
            "meta": {
                "provider": "huggingface",
                "model_id": model_name,
                "selected_provider": "huggingface",
                "selected_model_id": model_name,
                "max_new_tokens": max_new_tokens,
                "source": "thin_pipeline",
            },
        }

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **metadata: Any) -> dict[str, Any]:
        merged_context = dict(context or {})
        if metadata:
            merged_context["metadata"] = metadata
        return self.run(AIPipelineRequest(prompt=prompt, context=merged_context))

    def generate_text(self, text: str, model_name: str) -> dict[str, Any]:
        return self.run(
            AIPipelineRequest(
                prompt=text,
                context={"runtime_model_selection": {"provider": "huggingface", "model_id": model_name}},
            )
        )

    def provider_health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": "huggingface",
            "model_id": str(current_app.config.get("AI_MODEL_NAME") or ""),
            "source": "thin_pipeline",
        }

    def list_available_models(self) -> dict[str, Any]:
        model_name = str(current_app.config.get("AI_MODEL_NAME") or "").strip()
        models = [{"id": model_name, "source": "config_default"}] if model_name else []
        return {
            "model_defaults": {"provider": "huggingface", "model_name": model_name, "huggingface_model_id": model_name},
            "local": {"models": models, "count": len(models)},
            "huggingface_local": {"models": models, "count": len(models)},
            "models": [{"provider": "huggingface", "id": model_name}] if model_name else [],
        }


AIPipelineService = AIPipelineThinAdapter


def build_ai_service_from_config(*_, **__) -> AIPipelineThinAdapter:
    return AIPipelineThinAdapter()
