from __future__ import annotations

from typing import Any


class AIPipelineUpstreamError(RuntimeError):
    """Raised when upstream provider/model execution fails.

    Logic intent:
    - Expose stable exception type for API-layer error mapping.
    - Carry structured details for observability and client diagnostics.
    """

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def _upstream_details(*, exc: Exception, source: str) -> dict[str, str]:
    return {"exception": exc.__class__.__name__, "source": source}


def map_exception_to_upstream_error(exc: Exception) -> AIPipelineUpstreamError:
    """Normalize provider/runtime failures into a single typed upstream error."""
    if isinstance(exc, AIPipelineUpstreamError):
        return exc

    if isinstance(exc, FileNotFoundError):
        return AIPipelineUpstreamError(
            "AI provider resource not found",
            details=_upstream_details(exc=exc, source="provider_resource"),
        )

    if isinstance(exc, ValueError):
        return AIPipelineUpstreamError(
            "AI provider returned invalid output",
            details=_upstream_details(exc=exc, source="provider_parse"),
        )

    if isinstance(exc, RuntimeError):
        return AIPipelineUpstreamError(
            str(exc),
            details=_upstream_details(exc=exc, source="provider_runtime"),
        )

    if isinstance(exc, TypeError):
        return AIPipelineUpstreamError(
            "AI provider returned an invalid response payload",
            details=_upstream_details(exc=exc, source="provider_payload"),
        )

    return AIPipelineUpstreamError(
        "AI provider execution failed",
        details=_upstream_details(exc=exc, source="provider_unknown"),
    )


def invoke_provider_or_raise(provider: Any, request: Any) -> dict[str, Any]:
    """Invoke provider and raise only `AIPipelineUpstreamError` on failures."""
    try:
        payload = provider.invoke(request)
    except Exception as exc:  # noqa: BLE001
        raise map_exception_to_upstream_error(exc) from exc

    if not isinstance(payload, dict):
        raise map_exception_to_upstream_error(
            TypeError("Pipeline provider must return a dictionary")
        )

    return payload
