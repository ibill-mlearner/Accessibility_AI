from __future__ import annotations

from typing import Any

from ...utils.ai_checker import _normalize_interaction_response, _resolve_provider
from .interfaces import AIInteractionResponseNormalizerInterface


class AIInteractionResponseNormalizer(AIInteractionResponseNormalizerInterface):
    """Default response normalizer for AI interaction providers."""

    def normalize(self, result: Any) -> dict[str, Any]:
        normalized_result = _normalize_interaction_response(result)
        normalized_result["meta"]["provider"] = _resolve_provider(result)
        return normalized_result


def normalize_interaction_response(result: Any) -> dict[str, Any]:
    return AIInteractionResponseNormalizer().normalize(result)
