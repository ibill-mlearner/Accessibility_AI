from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ai_pipeline_contracts import AIPipelineRequest, AIPipelineServiceInterface


@dataclass(slots=True)
class PipelineContextRepository:
    config_system_content: str

    def build_system_content(self, request: AIPipelineRequest) -> str:
        if request.system_prompt:
            return request.system_prompt

        parts: list[str] = [self.config_system_content]

        from ..api.v1.routes import db
        from ..models import CourseClass, UserAccessibilityFeature

        if request.class_id:
            class_record = db.session.get(CourseClass, int(request.class_id))
            if class_record and class_record.description:
                parts.append(str(class_record.description).strip())

        if request.user_id:
            feature_rows = (
                db.session.query(UserAccessibilityFeature)
                .filter(
                    UserAccessibilityFeature.user_id == int(request.user_id),
                    UserAccessibilityFeature.enabled.is_(True),
                )
                .all()
            )
            for row in feature_rows:
                if row.accommodation and row.accommodation.details:
                    parts.append(str(row.accommodation.details).strip())

        return "\n\n".join(part for part in parts if part)


@dataclass(slots=True)
class PipelineInteractionRunner:
    model_name: str
    download_locally: bool
    max_new_tokens: int = 256

    def run(self, *, prompt: str, system_content: str) -> str:
        import ai_pipeline_thin.ai_pipeline as ai_tool

        pipeline = ai_tool.AIPipeline(
            model_name_value=self.model_name,
            system_content=system_content,
            prompt_value=prompt,
            download_locally=self.download_locally,
        )
        pipeline.model_loader.device_map = "auto"
        pipeline.model_loader.torch_dtype = "auto"

        model = pipeline.build_model()
        tokenizer = pipeline.build_tokenizer()
        text = pipeline.build_text(tokenizer=tokenizer)
        model_inputs = pipeline.build_model_inputs(tokenizer=tokenizer, text=text, model=model)
        raw_ids = pipeline.build_raw_generated_ids(model=model, model_inputs=model_inputs, max_new_tokens=self.max_new_tokens)
        generated_ids = pipeline.build_generated_ids(model_inputs=model_inputs, raw_generated_ids=raw_ids)
        return str(pipeline.build_response(tokenizer=tokenizer, generated_ids=generated_ids) or "").strip()


@dataclass(slots=True)
class AIPipelineService(AIPipelineServiceInterface):
    model_name: str
    context_repo: PipelineContextRepository
    interaction_runner: PipelineInteractionRunner

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        system_content = self.context_repo.build_system_content(request)
        assistant_text = self.interaction_runner.run(prompt=request.prompt, system_content=system_content)
        return {
            "assistant_text": assistant_text,
            "confidence": None,
            "notes": [],
            "meta": {"provider": "huggingface", "model": self.model_name},
        }

    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.run(
            AIPipelineRequest(
                prompt=prompt,
                context=context or {},
                messages=kwargs.get("messages") if isinstance(kwargs.get("messages"), list) else [],
                system_prompt=kwargs.get("system_prompt"),
                request_id=kwargs.get("request_id"),
                chat_id=kwargs.get("chat_id"),
                initiated_by=kwargs.get("initiated_by"),
                class_id=kwargs.get("class_id"),
                user_id=kwargs.get("user_id"),
                rag=kwargs.get("rag") if isinstance(kwargs.get("rag"), dict) else None,
            )
        )

    def list_available_models(self) -> dict[str, Any]:
        return {
            "model_defaults": {"provider": "huggingface", "model_name": self.model_name},
            "local": {"models": [{"id": self.model_name}], "count": 1},
            "huggingface_local": {"models": [{"id": self.model_name}], "count": 1},
        }

    def provider_health(self) -> dict[str, Any]:
        return {"huggingface": {"status": "configured", "model_id": self.model_name}}


def build_ai_service_from_config(module_config: dict[str, Any] | None, *, config: dict[str, Any] | None = None) -> AIPipelineService:
    cfg = module_config or {}
    app_cfg = config or {}
    model_name = str(cfg.get("model_name") or app_cfg.get("AI_MODEL_NAME") or "HuggingFaceTB/SmolLM2-360M-Instruct").strip()
    system_content = str(cfg.get("system_content") or app_cfg.get("AI_SYSTEM_CONTENT") or "You are a concise assistant.").strip()
    download_locally = bool(cfg.get("download_locally", app_cfg.get("AI_DOWNLOAD_LOCALLY", True)))
    max_new_tokens = int(cfg.get("max_new_tokens") or app_cfg.get("AI_MAX_NEW_TOKENS") or 256)

    return AIPipelineService(
        model_name=model_name,
        context_repo=PipelineContextRepository(config_system_content=system_content),
        interaction_runner=PipelineInteractionRunner(
            model_name=model_name,
            download_locally=download_locally,
            max_new_tokens=max_new_tokens,
        ),
    )
