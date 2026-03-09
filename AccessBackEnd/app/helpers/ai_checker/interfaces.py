from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class AIInteractionEnvelope:
    """Compact canonical interaction payload used across AI helper flows."""

    prompt: str
    assistant_text: str = ""
    provider: str = ""
    model_id: str = ""
    confidence: float | None = None
    notes: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


class AIInteractionMonolithInterface(Protocol):
    """Monolithic contract for normalize/validate/mutate/check AI payloads."""

    def normalize(self, payload: Any) -> AIInteractionEnvelope:
        """Build canonical envelope from provider or API payload."""

    def validate(self, envelope: AIInteractionEnvelope) -> None:
        """Raise ValueError when the envelope cannot be used safely."""

    def mutate(self, envelope: AIInteractionEnvelope, updates: dict[str, Any] | None = None) -> AIInteractionEnvelope:
        """Apply compact updates while preserving canonical envelope shape."""

    def check(self, envelope: AIInteractionEnvelope) -> dict[str, Any]:
        """Return health/debug checks for telemetry and diagnostics."""
