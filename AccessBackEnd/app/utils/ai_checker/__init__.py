from __future__ import annotations

from typing import Any

from .interfaces import (
    AIInteractionEnvelope,
    AIInteractionMonolithInterface,
    AIInteractionMutationsInterface,
    AIInteractionValidatorInterface,
    AIModelArtifactOpsInterface,
)
from .model_artifacts import AIModelArtifactOps, has_valid_model_artifacts, local_model_dir, model_artifact_diagnostics
from .mutations import AIInteractionMutations
from .operations import sync_ai_models_with_local_inventory
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
    "AIModelArtifactOpsInterface",
    "AIModelArtifactOps",
    "model_artifact_diagnostics",
    "has_valid_model_artifacts",
    "local_model_dir",
    "sync_ai_models_with_local_inventory",
]
