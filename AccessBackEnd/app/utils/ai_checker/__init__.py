from __future__ import annotations

from typing import Any

from .interfaces import (
    AIInteractionEnvelope,
    AIInteractionMonolithInterface,
    AIInteractionMutationsInterface,
    AIInteractionValidatorInterface,
    AIInteractionHelperOpsInterface,
    AIModelInventoryHelpersInterface,
    AIModelInventoryOperationsInterface,
    AIModelArtifactOpsInterface,
)
from .model_artifacts import AIModelArtifactOps
from .mutations import AIInteractionMutations
from .operations import AIModelInventoryHelpers, AIModelInventoryOperations, discover_local_model_inventory, sync_ai_models_with_local_inventory
from .interaction_helpers import (
    AIInteractionHelperOps,
    derive_selection_from_chat,
    normalize_interaction_response,
    persist_interaction,
    resolve_chat_id,
    resolve_initiated_by,
)
from .validators import AIInteractionValidator


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
    "AIInteractionMonolith",
    "AIInteractionValidator",
    "AIInteractionHelperOpsInterface",
    "AIModelInventoryHelpersInterface",
    "AIModelInventoryOperationsInterface",
    "AIModelArtifactOpsInterface",
    "AIModelArtifactOps",
    "AIModelInventoryHelpers",
    "AIModelInventoryOperations",
    "AIInteractionHelperOps",
    "discover_local_model_inventory",
    "sync_ai_models_with_local_inventory",
    "derive_selection_from_chat",
    "normalize_interaction_response",
    "persist_interaction",
    "resolve_chat_id",
    "resolve_initiated_by",
]
