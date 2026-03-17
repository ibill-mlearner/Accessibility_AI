from __future__ import annotations

from typing import Any, Protocol

from ..ai_pipeline_v2.types import AIPipelineConfig, AIPipelineRequest


class AIProviderInterface(Protocol):
    """Provider contract consumed by the slim AI pipeline service."""

    def generate(self, prompt: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]: ...
    def invoke(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...
    def inventory(self) -> list[dict[str, Any]]: ...
    def name(self) -> str: ...


class AIProviderFactoryInterface(Protocol):
    """Factory contract for model-specific provider/client instances."""

    def __call__(self, config: AIPipelineConfig, *, model_id: str) -> AIProviderInterface: ...


class AIPipelineServiceInterface(Protocol):
    """App-facing AI service contract used by APIs and helper services."""

    def run(self, request: AIPipelineRequest) -> dict[str, Any]: ...
    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None, **metadata: Any) -> dict[str, Any]: ...
    def generate_text(self, text: str, model_name: str) -> dict[str, Any]: ...
    def provider_health(self) -> dict[str, Any]: ...
    def list_available_models(self) -> dict[str, Any]: ...


class ProviderModelSelectionResolverInterface(Protocol):
    """Contract used to resolve provider/model selection from request payloads."""

    def __call__(
        self,
        payload: dict[str, Any],
        ai_service: "AIPipelineServiceInterface",
        *,
        allow_session: bool = True,
        require_explicit: bool = False,
        inventory_payload: dict[str, Any] | None = None,
    ) -> dict[str, str]: ...


class CatalogModelSelectionResolverInterface(Protocol):
    """Contract for catalog model-selection resolution based on persisted context."""

    def __call__(
        self,
        *,
        persisted_selection: dict[str, Any] | None,
        active_user_id: int | None,
        active_session_id: int | None,
        config_provider: str,
        config_model_id: str,
        available_by_provider: dict[str, set[str]],
        ordered_models: list[dict[str, Any]],
    ) -> dict[str, str]: ...
