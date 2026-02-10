from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


class AIPipelineService:
    """AI interaction gateway that can use a live endpoint or local mock JSON."""

    def __init__(self, *, provider: str, mock_resource_path: str, live_endpoint: str, timeout_seconds: int = 60) -> None:
        self.provider = (provider or "mock_json").strip().lower()
        self.mock_resource_path = mock_resource_path
        self.live_endpoint = live_endpoint
        self.timeout_seconds = timeout_seconds

    def run_interaction(self, prompt: str) -> dict:
        if self.provider in {"mock", "mock_json", "json"}:
            return self._from_mock_json(prompt)
        if self.provider in {"live", "live_agent", "http"}:
            return self._from_live_endpoint(prompt)

        raise ValueError(f"Unsupported AI provider: {self.provider}")

    def _from_mock_json(self, prompt: str) -> dict:
        resource = Path(self.mock_resource_path)
        if not resource.exists():
            raise FileNotFoundError(f"Mock AI resource not found: {resource}")

        payload = json.loads(resource.read_text(encoding="utf-8"))
        payload.setdefault("meta", {})
        payload["meta"]["provider"] = "mock_json"
        payload["meta"]["prompt_echo"] = prompt
        return payload

    def _from_live_endpoint(self, prompt: str) -> dict:
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
            parsed["meta"]["provider"] = "live"
        return parsed
