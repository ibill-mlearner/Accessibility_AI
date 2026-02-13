"""Backward-compatible module path for AI pipeline service.

# Intent:
# - Preserve imports that reference `app.services.ai_pipeline_service`.
# - Delegate actual implementation to the new `app.services.ai_service` package.
"""

from .ai_service.pipeline import AIPipelineService

__all__ = ["AIPipelineService"]
