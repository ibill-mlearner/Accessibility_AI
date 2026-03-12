from __future__ import annotations

from .interfaces import AIInteractionComponents
from .model_resolution import AIInteractionModelResolver
from .persistence import AIInteractionPersistence
from .request_parsing import AIInteractionRequestParser
from .response_normalization import AIInteractionResponseNormalizer


def default_ai_interaction_components() -> AIInteractionComponents:
    """Build default interface-backed components for AI interaction orchestration."""
    return AIInteractionComponents(
        request_parser=AIInteractionRequestParser(),
        model_resolver=AIInteractionModelResolver(),
        persistence=AIInteractionPersistence(),
        response_normalizer=AIInteractionResponseNormalizer(),
    )
