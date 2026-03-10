from __future__ import annotations

from typing import Any

from .interfaces import (
    AIInteractionEnvelope,
    AIInteractionMonolithInterface,
    AIInteractionMutationsInterface,
    AIInteractionValidatorInterface,
)
from .mutations import AIInteractionMutations
from .operations import AIInteractionOps
from .validators import AIInteractionValidator

from .operations import (
    _extract_response_text,
    _truncate_debug_payload,
    _strip_prompt_template_echo,
    _normalize_interaction_response,
    _resolve_selected_model,
    _extract_available_model_ids,
    _resolve_initiated_by,
    _resolve_system_instructions,
    _resolve_provider,
    _resolve_ai_model_id,
    _resolve_prompt_link_id,
    _resolve_chat_id,
    _build_interaction_persistence_payload,
    _sync_chat_latest_interaction,
    _resolve_session_model_selection,
    _persist_ai_interaction,
    compose_system_prompt,
    validate_runtime_model_selection,
    classify_upstream_error,
    build_prompt_and_messages,
    build_context_and_system_instructions,
    resolve_model_override,
    run_pipeline,
    sync_ai_models_with_local_inventory,
    resolve_model_selection,
)


class AIInteractionMonolith(AIInteractionMonolithInterface):
    """Compressed helper that centralizes AI payload normalize/validate/mutate/check."""

    def normalize(self, payload: Any) -> AIInteractionEnvelope:
        return AIInteractionMutations.normalize_payload(payload)

    def validate(self, envelope: AIInteractionEnvelope) -> None:
        AIInteractionValidator.validate_envelope(envelope)

    def mutate(self, envelope: AIInteractionEnvelope, updates: dict[str, Any] | None = None) -> AIInteractionEnvelope:
        return AIInteractionMutations.mutate_envelope(envelope, updates)

    def check(self, envelope: AIInteractionEnvelope) -> dict[str, Any]:
        return AIInteractionValidator.check_envelope(envelope)


__all__ = [
    "AIInteractionEnvelope",
    "AIInteractionValidatorInterface",
    "AIInteractionMutationsInterface",
    "AIInteractionMonolithInterface",
    "AIInteractionMutations",
    "AIInteractionOps",
    "AIInteractionMonolith",
    "AIInteractionValidator",
    "_extract_response_text",
    "_truncate_debug_payload",
    "_strip_prompt_template_echo",
    "_normalize_interaction_response",
    "_resolve_selected_model",
    "_extract_available_model_ids",
    "_resolve_initiated_by",
    "_resolve_system_instructions",
    "_resolve_provider",
    "_resolve_ai_model_id",
    "_resolve_prompt_link_id",
    "_resolve_chat_id",
    "_build_interaction_persistence_payload",
    "_sync_chat_latest_interaction",
    "_resolve_session_model_selection",
    "_persist_ai_interaction",
    "compose_system_prompt",
    "validate_runtime_model_selection",
    "classify_upstream_error",
    "build_prompt_and_messages",
    "build_context_and_system_instructions",
    "resolve_model_override",
    "run_pipeline",
    "sync_ai_models_with_local_inventory",
    "resolve_model_selection",
]
