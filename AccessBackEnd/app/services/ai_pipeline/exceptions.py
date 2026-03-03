from __future__ import annotations

from typing import Any


class AIPipelineUpstreamError(RuntimeError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def map_exception_to_upstream_error(exc: Exception) -> AIPipelineUpstreamError:
    if isinstance(exc, AIPipelineUpstreamError):
        return exc
    if isinstance(exc, FileNotFoundError):
        return AIPipelineUpstreamError("AI provider resource not found", details={"source": "provider_resource", "exception": exc.__class__.__name__})
    if isinstance(exc, ValueError):
        return AIPipelineUpstreamError("AI provider returned invalid output", details={"source": "provider_parse", "exception": exc.__class__.__name__})
    if isinstance(exc, TypeError):
        return AIPipelineUpstreamError("AI provider returned an invalid response payload", details={"source": "provider_payload", "exception": exc.__class__.__name__})
    return AIPipelineUpstreamError(str(exc) or "AI provider execution failed", details={"source": "provider_runtime", "exception": exc.__class__.__name__})


def invoke_provider_or_raise(provider: Any, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        payload = provider.invoke(prompt, context or {})
    except Exception as exc:  # noqa: BLE001
        raise map_exception_to_upstream_error(exc) from exc
    if not isinstance(payload, dict):
        raise map_exception_to_upstream_error(TypeError("Pipeline provider must return a dictionary"))
    return payload
