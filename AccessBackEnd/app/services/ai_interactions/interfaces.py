from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ...services.ai_pipeline_slim import AIPipelineServiceInterface
from ...services.ai_pipeline_v2.types import AIPipelineRequest


@dataclass(frozen=True)
class AIInteractionRequestDTOBuild:
    payload: dict[str, Any]
    prompt: str
    messages: list[dict[str, Any]]
    context_payload: dict[str, Any]
    system_instructions: str
    composed_system_prompt: str
    chat_id: int | None
    initiated_by: str
    request_id: str
    dto: AIPipelineRequest


class AIInteractionRequestParserInterface(Protocol):
    def parse_payload(self) -> dict[str, Any]:
        ...

    def build_request_dto(self, payload: dict[str, Any]) -> AIInteractionRequestDTOBuild:
        ...


class AIInteractionModelResolverInterface(Protocol):
    def resolve_runtime_model_selection(
        self,
        payload: dict[str, Any],
        ai_service: AIPipelineServiceInterface,
        context_payload: dict[str, Any],
        request_id: str,
    ):
        ...


class AIInteractionPersistenceInterface(Protocol):
    def persist(self, payload: dict[str, Any], prompt: str, normalized_result: dict[str, Any]):
        ...


class AIInteractionResponseNormalizerInterface(Protocol):
    def normalize(self, result: Any) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class AIInteractionComponents:
    request_parser: AIInteractionRequestParserInterface
    model_resolver: AIInteractionModelResolverInterface
    persistence: AIInteractionPersistenceInterface
    response_normalizer: AIInteractionResponseNormalizerInterface
