from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


class BaseAIProvider:
    """Contract for all AI providers used by the pipeline.

    # Intent:
    # - Keep provider logic isolated so this folder can be promoted to a standalone package.
    # - Enable drop-in providers (mock JSON, HTTP gateway, LangChain, HuggingFace local models).
    # - Standardize output shape so callers can always expect a JSON-compatible dictionary.
    """

    def run(self, prompt: str) -> dict:
        # Intent: subclasses should implement prompt execution and return JSON-compatible results.
        raise NotImplementedError


class MockJSONProvider(BaseAIProvider):
    """Load deterministic responses from disk for local development and CI."""

    def __init__(self, *, mock_resource_path: str) -> None:
        # Intent: only depend on a file path so this provider is simple to use in a hello-world app.
        self.mock_resource_path = mock_resource_path

    def run(self, prompt: str) -> dict:
        # Intent:
        # 1) Read a local JSON fixture.
        # 2) Attach metadata (provider + prompt echo) to support downstream debugging.
        # 3) Return a dictionary that mirrors a real model response schema.
        resource = Path(self.mock_resource_path)
        if not resource.exists():
            raise FileNotFoundError(f"Mock AI resource not found: {resource}")

        payload = json.loads(resource.read_text(encoding="utf-8"))
        payload.setdefault("meta", {})
        payload["meta"]["provider"] = "mock_json"
        payload["meta"]["prompt_echo"] = prompt
        return payload


class HTTPEndpointProvider(BaseAIProvider):
    """Call a network AI endpoint that accepts and returns JSON."""

    def __init__(self, *, live_endpoint: str, timeout_seconds: int = 60) -> None:
        # Intent: make endpoint and timeout configurable so service can run against any API host.
        self.live_endpoint = live_endpoint
        self.timeout_seconds = timeout_seconds

    def run(self, prompt: str) -> dict:
        # Intent:
        # 1) POST the prompt as JSON.
        # 2) Parse and return JSON output.
        # 3) Add provider metadata to keep outputs normalized across provider implementations.
        if not self.live_endpoint:
            raise ValueError("AI live endpoint is not configured")

        request_body = json.dumps({"prompt": prompt}).encode("utf-8")
        request = Request(
            self.live_endpoint,
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read().decode("utf-8")
        except URLError as exc:  # pragma: no cover - network dependent
            raise RuntimeError(f"Failed to call live AI endpoint: {exc}") from exc

        parsed = json.loads(content or "{}")
        if isinstance(parsed, dict):
            parsed.setdefault("meta", {})
            parsed["meta"]["provider"] = "live_http"
        return parsed


class HuggingFaceLangChainProvider(BaseAIProvider):
    """Planned provider for local or downloaded HuggingFace models via LangChain.

    # Intent:
    # - Use modern MIT-licensed packages in the LangChain ecosystem where possible.
    # - Support first-run model download at app install/bootstrap time.
    # - Return structured JSON output for backend consumers.
    """

    def __init__(self, *, model_id: str, cache_dir: str | None = None) -> None:
        # Intent: store model selection and cache location for future bootstrap + offline reuse.
        self.model_id = model_id
        self.cache_dir = cache_dir

    def run(self, prompt: str) -> dict:
        # Intent (future implementation):
        # 1) Initialize HuggingFace pipeline/model if absent (download + cache).
        # 2) Wrap model with LangChain runnable chain and JSON output parser.
        # 3) Execute prompt and return validated JSON dictionary.
        raise NotImplementedError("HuggingFaceLangChainProvider is planned for a future sprint")
