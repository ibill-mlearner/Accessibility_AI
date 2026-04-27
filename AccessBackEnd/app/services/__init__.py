"""Service layer package surface.

The AI execution gateway (`AIPipelineGateway`) is the primary service entry point used by API routes to run interactions, resolve active model selection, and return normalized response metadata. It keeps runtime/provider orchestration centralized so route handlers do not directly couple to provider-specific loading logic.

Logging bootstrap wrappers are initialized during app startup and attach an event bus plus default observers while preserving existing route/service call sites. The bootstrap also wraps the configured AI service with an interaction-logging decorator so prompts/responses can be recorded without changing route code. In short, logging concerns are layered around the service at startup time rather than mixed into each API handler.

Supporting demo utilities in this folder are developer/admin-oriented helper scripts kept for local validation and troubleshooting workflows.
"""

__all__ = ["AIPipelineGateway"]
