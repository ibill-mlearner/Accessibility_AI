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


class AIInteractionValidatorInterface(Protocol):
    """Stateless sanitizer/normalizer contract shared across AI helpers."""

    @staticmethod
    def to_clean_text(value: Any, *, lower: bool = False) -> str: ...

    @staticmethod
    def to_clean_model_id(value: Any) -> str: ...

    @staticmethod
    def to_optional_float(value: Any) -> float | None: ...

    @staticmethod
    def to_clean_notes(value: Any) -> list[str]: ...

    @staticmethod
    def resolve_help_intent(value: Any, *, default: str = "summarization") -> str: ...


    @staticmethod
    def validate_envelope(envelope: AIInteractionEnvelope) -> None: ...

    @staticmethod
    def check_envelope(envelope: AIInteractionEnvelope) -> dict[str, Any]: ...


class AIInteractionMutationsInterface(Protocol):
    """Stateless transformation contract for envelope/response mutation flows."""

    @staticmethod
    def normalize_payload(payload: Any) -> AIInteractionEnvelope: ...

    @staticmethod
    def mutate_envelope(envelope: AIInteractionEnvelope, updates: dict[str, Any] | None = None) -> AIInteractionEnvelope: ...

    @staticmethod
    def strip_prompt_template_echo(text: str) -> str: ...

    @staticmethod
    def truncate_debug_payload(value: Any, *, limit: int = 1200) -> str: ...


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


class AIModelArtifactOpsInterface(Protocol):
    path: Any
    config_file: Any

    def model_artifact_diagnostics(self) -> dict[str, Any]: ...

    def has_valid_model_artifacts(self) -> bool: ...

    @staticmethod
    def diagnostics_for_path(path: Any) -> dict[str, Any]: ...

    @staticmethod
    def has_valid_artifacts_for_path(path: Any) -> bool: ...

    @staticmethod
    def local_model_dir(project_root: Any, model_id: str): ...


class AIModelInventoryHelpersInterface(Protocol):
    @staticmethod
    def discover_model_ids(models_root: Any) -> list[str]: ...

    @staticmethod
    def resolve_local_models_root(app: Any): ...

    @staticmethod
    def resolve_installed_pipeline_models_root(): ...


class AIModelInventoryOperationsInterface(Protocol):
    def discover_local_model_inventory(self) -> dict[str, Any]: ...

    def sync_ai_models_with_local_inventory(self) -> dict[str, Any]: ...


class AIInteractionHelperOpsInterface(Protocol):
    current_ai_model_id: int | None

    def derive_selection_from_chat(self, chat: Any) -> tuple[str, str]: ...

    def resolve_chat_id(self, payload: dict[str, Any]) -> int | None: ...

    def resolve_initiated_by(self, payload: dict[str, Any]) -> str: ...

    def normalize_interaction_response(self, result: Any) -> dict[str, Any]: ...

    def resolve_ai_model_id(self, result: Any, *, db_session: Any) -> int: ...

    def persist_interaction(
        self,
        *,
        payload: dict[str, Any],
        prompt: str,
        normalized_result: dict[str, Any],
        db_session: Any,
        require_record: Any,
    ) -> tuple[Any, int] | None: ...
