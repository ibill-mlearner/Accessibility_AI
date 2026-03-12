from __future__ import annotations

from ...utils.ai_checker import _persist_ai_interaction
from .interfaces import AIInteractionPersistenceInterface


class AIInteractionPersistence(AIInteractionPersistenceInterface):
    """Default persistence adapter for AI interactions."""

    def persist(self, payload: dict[str, object], prompt: str, normalized_result: dict[str, object]):
        return _persist_ai_interaction(payload, prompt, normalized_result)


def persist_ai_interaction(payload: dict[str, object], prompt: str, normalized_result: dict[str, object]):
    return AIInteractionPersistence().persist(payload, prompt, normalized_result)
