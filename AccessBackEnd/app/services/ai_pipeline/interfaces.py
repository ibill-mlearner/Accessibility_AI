from __future__ import annotations

from typing import Any, Protocol

from .types import AIPipelineRequest


class AIProviderInterface(Protocol):
    """Provider contract consumed by the AI pipeline service."""

    def invoke(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        ...

    def health(self) -> dict[str, Any]:
        ...


class AIProviderFactoryInterface(Protocol):
    """Factory contract for creating provider implementations."""

    def __call__(
        self,
        *,
        provider: str,
        model_name: str = "",
        mock_resource_path: str = "",
        live_endpoint: str = "",
        ollama_endpoint: str = "",
        ollama_model_id: str = "",
        ollama_options: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
        huggingface_model_id: str = "",
        huggingface_cache_dir: str | None = None,
        max_new_tokens: int = 256,
        temperature: float = 0.1,
    ) -> AIProviderInterface:
        ...


class ModelInventoryServiceInterface(Protocol):
    """Read-only model inventory contract."""

    def list_available_models(self) -> dict[str, Any]:
        ...


class ModelInventoryServiceFactoryInterface(Protocol):
    """Factory contract for creating model inventory services."""

    def __call__(self, config: Any) -> ModelInventoryServiceInterface:
        ...


class AIPipelineServiceInterface(Protocol):
    """Stable interface for pipeline orchestration and model introspection."""

    def run(self, request: AIPipelineRequest) -> dict[str, Any]:
        ...

    def run_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> dict[str, Any]:
        ...

    def provider_health(self) -> dict[str, Any]:
        ...

    def list_available_models(self) -> dict[str, Any]:
        ...


class ModelReconciliationServiceInterface(Protocol):
    """Contract for syncing discovered model inventory into persistence."""

    def reconcile(self) -> dict[str, int]:
        ...