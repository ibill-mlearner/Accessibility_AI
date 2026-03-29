from __future__ import annotations

import importlib
from typing import Any

from flask import current_app, has_app_context

from ..extensions import db
from ..models import AIModel, Accommodation, AccommodationSystemPrompt, SystemPrompt


class AIPipelineGateway:
    """Standalone gateway class mirroring demo_v2 pipeline behavior."""

    def __init__(self, *, config: dict[str, Any] | None = None, module_config: dict[str, Any] | None = None) -> None:
        cfg = module_config or {}
        app_cfg = config or {}
        self._configured_model_name = str(
            cfg.get("model_name")
            or app_cfg.get("AI_MODEL_NAME")
            or ""
        ).strip()

    @staticmethod
    def _load_ai_tool() -> Any:
        candidates = (
            "ai_pipeline_thin.ai_pipeline",
            "app.services.ai_pipeline_thin.ai_pipeline",
            "AccessBackEnd.app.services.ai_pipeline_thin.ai_pipeline",
        )
        for module_path in candidates:
            try:
                return importlib.import_module(module_path)
            except ModuleNotFoundError:
                continue
        raise ModuleNotFoundError(
            "No module named 'ai_pipeline_thin'. Install the ai runtime package or provide a local "
            "AccessBackEnd.app.services.ai_pipeline_thin.ai_pipeline module."
        )

    @staticmethod
    def _resolve_active_model_name() -> str:
        configured_model = current_app.config.get("AI_MODEL_NAME")
        if isinstance(configured_model, str) and configured_model:
            return configured_model

        active_model = (
            db.session.query(AIModel)
            .filter(AIModel.active.is_(True))
            .order_by(AIModel.updated_at.desc(), AIModel.id.desc())
            .first()
        )
        if active_model and isinstance(active_model.model_id, str) and active_model.model_id:
            return active_model.model_id

        raise RuntimeError("Unable to resolve model name from AI_MODEL_NAME config or active AIModel database row.")

    @staticmethod
    def _fetch_accessibility_prompt_texts() -> list[str]:
        parts: list[str] = []
        seen: set[str] = set()

        prompt_rows = db.session.query(SystemPrompt.text).order_by(SystemPrompt.id.asc()).all()
        for (prompt_text,) in prompt_rows:
            normalized = str(prompt_text).strip() if prompt_text else ""
            if normalized and normalized not in seen:
                parts.append(normalized)
                seen.add(normalized)

        linked_rows = (
            db.session.query(Accommodation.details)
            .join(
                AccommodationSystemPrompt,
                AccommodationSystemPrompt.accommodation_id == Accommodation.id,
            )
            .filter(Accommodation.active.is_(True))
            .order_by(Accommodation.id.asc())
            .all()
        )
        for (details,) in linked_rows:
            normalized = str(details).strip() if details else ""
            if normalized and normalized not in seen:
                parts.append(normalized)
                seen.add(normalized)

        active_accommodation_rows = (
            db.session.query(Accommodation.details)
            .filter(Accommodation.active.is_(True))
            .order_by(Accommodation.id.asc())
            .all()
        )
        for (details,) in active_accommodation_rows:
            normalized = str(details).strip() if details else ""
            if normalized and normalized not in seen:
                parts.append(normalized)
                seen.add(normalized)

        return parts

    @staticmethod
    def _build_system_content() -> str:
        guardrail_prompt = current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT")
        if not isinstance(guardrail_prompt, str) or not guardrail_prompt:
            raise RuntimeError("AI_SYSTEM_GUARDRAIL_PROMPT is required for ai pipeline gateway and was not found in Flask config.")

        accessibility_prompts = AIPipelineGateway._fetch_accessibility_prompt_texts()
        parts: list[str] = [guardrail_prompt]
        if accessibility_prompts:
            parts.append("\n\n".join(accessibility_prompts))
        return "\n\n".join(part for part in parts if part)

    def run(self, prompt: str, *, model_name: str | None = None, system_content: str | None = None) -> dict[str, Any]:
        ai_tool = self._load_ai_tool()
        resolved_model = model_name or self._resolve_active_model_name()
        resolved_system_content = system_content or self._build_system_content()

        pipeline = ai_tool.AIPipeline(
            model_name_value=resolved_model,
            system_content=resolved_system_content,
            prompt_value=prompt,
            download_locally=bool(current_app.config.get("AI_DOWNLOAD_LOCALLY", True)),
        )

        pipeline.model_loader.device_map = "auto"
        if hasattr(pipeline.model_loader, "dtype"):
            pipeline.model_loader.dtype = "auto"
        else:
            pipeline.model_loader.torch_dtype = "auto"

        model = pipeline.build_model()
        tokenizer = pipeline.build_tokenizer()
        text = pipeline.build_text(tokenizer=tokenizer)
        model_inputs = pipeline.build_model_inputs(tokenizer=tokenizer, text=text, model=model)
        raw_ids = pipeline.build_raw_generated_ids(
            model=model,
            model_inputs=model_inputs,
            max_new_tokens=int(current_app.config.get("AI_MAX_NEW_TOKENS", 100)),
        )
        generated_ids = pipeline.build_generated_ids(model_inputs=model_inputs, raw_generated_ids=raw_ids)
        assistant_text = str(pipeline.build_response(tokenizer=tokenizer, generated_ids=generated_ids) or "").strip()

        return {
            "assistant_text": assistant_text,
            "confidence": None,
            "notes": [],
            "meta": {
                "provider": "huggingface",
                "model": resolved_model,
                "selected_provider": "huggingface",
                "selected_model_id": resolved_model,
            },
        }

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        selected_model: str | None = None
        if isinstance(context, dict):
            runtime_selection = context.get("runtime_model_selection")
            if isinstance(runtime_selection, dict):
                selected_model = str(runtime_selection.get("model_id") or "").strip() or None

        response = self.run(
            prompt,
            model_name=selected_model,
            system_content=kwargs.get("system_prompt"),
        )

        if isinstance(context, dict):
            runtime_selection = context.get("runtime_model_selection")
            if isinstance(runtime_selection, dict):
                selected_provider = str(runtime_selection.get("provider") or "huggingface").strip() or "huggingface"
                selected_model_id = str(runtime_selection.get("model_id") or response["meta"]["selected_model_id"]).strip()
                selected_source = str(runtime_selection.get("source") or "").strip()
                response["meta"]["provider"] = selected_provider
                response["meta"]["model"] = selected_model_id
                response["meta"]["selected_provider"] = selected_provider
                response["meta"]["selected_model_id"] = selected_model_id
                if selected_source:
                    response["meta"]["source"] = selected_source
                    response["meta"]["selected_source"] = selected_source

        return response

    def list_available_models(self) -> dict[str, Any]:
        if has_app_context():
            model_name = str(current_app.config.get("AI_MODEL_NAME") or "").strip() or self._resolve_active_model_name()
        else:
            model_name = self._configured_model_name
        return {
            "model_defaults": {"provider": "huggingface", "model_name": model_name},
            "local": {"models": [{"id": model_name}], "count": 1},
            "huggingface_local": {"models": [{"id": model_name}], "count": 1},
        }

    def provider_health(self) -> dict[str, Any]:
        if has_app_context():
            model_name = str(current_app.config.get("AI_MODEL_NAME") or "").strip() or self._resolve_active_model_name()
        else:
            model_name = self._configured_model_name
        return {"status": "configured", "provider": "huggingface", "model_id": model_name}
