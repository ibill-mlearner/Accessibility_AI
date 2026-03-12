from __future__ import annotations
from dataclasses import asdict
from flask import current_app
from flask_login import current_user

from ...api.v1.routes import BadRequestError, _read_json_object, _validate_payload
from ...schemas.validation import AIInteractionPayloadSchema
from ...services.ai_pipeline.types import AIPipelineRequest
from ...utils.ai_checker import (
    _resolve_chat_id,
    _resolve_initiated_by,
    build_context_and_system_instructions,
    build_prompt_and_messages,
    compose_system_prompt,
)
from .interfaces import AIInteractionRequestDTOBuild, AIInteractionRequestParserInterface


class AIInteractionRequestParser(AIInteractionRequestParserInterface):
    """Default parser/DTO builder for AI interaction requests."""

    def parse_payload(self) -> dict[str, object]:
        raw = _read_json_object()
        current_app.logger.debug(
            "api.ai.interactions.payload.raw path=%s json_keys=%s",
            "/api/v1/ai/interactions",
            sorted(raw.keys()),
        )

        try:
            payload = _validate_payload(_read_json_object(), AIInteractionPayloadSchema())
        except BadRequestError:
            current_app.logger.debug(
                "api.ai.interactions.payload.validation_failed path=%s json_keys=%s",
                "/api/v1/ai/interactions",
                sorted(raw.keys()),
            )
            raise

        current_app.logger.debug(
            "api.ai.interactions.payload.validated keys=%s",
            sorted(payload.keys()),
        )
        user_identity = (
            getattr(current_user, "email", None)
            or getattr(current_user, "id", None)
            or "anonymous"
        )
        current_app.logger.debug(
            "api.ai_interactions.request method=%s path=%s user=%s json_keys=%s",
            "POST",
            "/api/v1/ai/interactions",
            user_identity,
            sorted(payload.keys()),
        )
        return payload

    def build_request_dto(
            self,
            payload: dict[str, object]
    ) -> AIInteractionRequestDTOBuild:
        prompt, messages = build_prompt_and_messages(payload)
        context_payload, system_instructions = build_context_and_system_instructions(payload, messages)
        composed_system_prompt = compose_system_prompt(system_instructions, payload)
        chat_id = _resolve_chat_id(payload)
        initiated_by = _resolve_initiated_by(payload)
        request_id = str(payload.get("request_id") or "n/a")

        current_app.logger.info(
            "api.ai.interactions.dto.build_input prompt=%r messages=%r system_prompt=%r context=%r chat_id=%r initiated_by=%r class_id=%r user_id=%r rag=%r request_id=%r",
            prompt,
            messages,
            composed_system_prompt,
            context_payload,
            chat_id,
            initiated_by,
            payload.get("class_id"),
            payload.get("user_id"),
            payload.get("rag") if isinstance(payload.get("rag"), dict) else None,
            payload.get("request_id"),
        )

        dto = AIPipelineRequest(
            prompt=prompt,
            messages=messages,
            system_prompt=composed_system_prompt,
            context=context_payload,
            chat_id=chat_id,
            initiated_by=initiated_by,
            class_id=payload.get("class_id"),
            user_id=payload.get("user_id"),
            rag=payload.get("rag") if isinstance(payload.get("rag"), dict) else None,
            request_id=payload.get("request_id"),
        )

        current_app.logger.info(
            "api.ai.interactions.dto.built dto=%r",
            asdict(dto),
        )

        return AIInteractionRequestDTOBuild(
            payload=payload,
            prompt=prompt,
            messages=messages,
            context_payload=context_payload,
            system_instructions=system_instructions,
            composed_system_prompt=composed_system_prompt,
            chat_id=chat_id,
            initiated_by=initiated_by,
            request_id=request_id,
            dto=dto,
        )


def parse_ai_interaction_payload() -> dict[str, object]:
    return AIInteractionRequestParser().parse_payload()


def build_request_dto(payload: dict[str, object]) -> AIInteractionRequestDTOBuild:
    return AIInteractionRequestParser().build_request_dto(payload)
