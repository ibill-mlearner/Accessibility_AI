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
]