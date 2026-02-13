from __future__ import annotations

from .providers import BaseAIProvider, HTTPEndpointProvider, HuggingFaceLangChainProvider, MockJSONProvider


class AIPipelineService:
    """Orchestrate provider selection and JSON-first AI interactions.

    # Architecture intent:
    # - Keep this folder package-ready so it can be imported into a minimal hello-world app.
    # - Split responsibilities into: provider selection, prompt execution, and response normalization.
    # - Provide a single `run_interaction(prompt)` entry point for the rest of the backend.
    # - Allow evolution toward LangChain pipelines without changing the app integration contract.
    """

    def __init__(
        self,
        *,
        provider: str,
        mock_resource_path: str,
        live_endpoint: str,
        timeout_seconds: int = 60,
        huggingface_model_id: str = "",
        huggingface_cache_dir: str | None = None,
    ) -> None:
        # Intent:
        # 1) Capture runtime configuration in one place.
        # 2) Select the provider implementation once at startup.
        # 3) Keep constructor args explicit for portability into a standalone package.
        self.provider = (provider or "mock_json").strip().lower()
        self.mock_resource_path = mock_resource_path
        self.live_endpoint = live_endpoint
        self.timeout_seconds = timeout_seconds
        self.huggingface_model_id = huggingface_model_id
        self.huggingface_cache_dir = huggingface_cache_dir

        self._provider_client = self._select_provider()

    def _select_provider(self) -> BaseAIProvider:
        # Intent:
        # - Centralize provider routing logic.
        # - Keep aliases to support migration from existing config values.
        # - Make it easy to register additional providers in future sprints.
        if self.provider in {"mock", "mock_json", "json"}:
            return MockJSONProvider(mock_resource_path=self.mock_resource_path)

        if self.provider in {"live", "live_agent", "http"}:
            return HTTPEndpointProvider(
                live_endpoint=self.live_endpoint,
                timeout_seconds=self.timeout_seconds,
            )

        if self.provider in {"hf", "huggingface", "langchain_hf"}:
            return HuggingFaceLangChainProvider(
                model_id=self.huggingface_model_id,
                cache_dir=self.huggingface_cache_dir,
            )

        raise ValueError(f"Unsupported AI provider: {self.provider}")

    def run_interaction(self, prompt: str) -> dict:
        # Intent:
        # 1) Execute the selected provider.
        # 2) Enforce dictionary-like JSON output for API consistency.
        # 3) Attach top-level pipeline metadata so callers can audit execution path.
        payload = self._provider_client.run(prompt)
        if not isinstance(payload, dict):
            raise TypeError("AI pipeline output must be a dictionary")

        payload.setdefault("meta", {})
        payload["meta"]["pipeline"] = "app.services.ai_service"
        return payload
