# AI Pipeline Thin: Request Data Contract (Trust-the-Module Guidance)

This document describes the **minimum data shape** the API layer should pass through so `ai_pipeline_thin` can do the heavy lifting.

## Goal

Keep application adapters thin:
- pass clean request data through,
- avoid duplicating model-id normalization/parsing logic in multiple backend files,
- let the pipeline module own model loading and model-id interpretation.

## Required inputs for interaction execution

For `POST /api/v1/ai/interactions`, the backend should provide:

- `prompt` (`str`): user input text to generate on.
- `system_prompt` (`str | None`): composed guardrail + accessibility instructions.
- `messages` (`list[dict]`): optional chat history, if present.
- `context` (`dict`): optional metadata bag (chat/session/runtime metadata).

These values are wrapped in `AIPipelineRequest` and passed to the AI service.

## Model selection inputs

Model selection should rely on these existing sources only:
1. explicit request override (`provider`, `model_id`),
2. persisted session selection,
3. configured defaults.

### Important constraint

`model_id` should be treated as an opaque identifier in the API layer.
- Do **not** transform, lowercase, split, or canonicalize path/repo segments in route/service glue code.
- Forward the value as provided; the pipeline module is responsible for interpreting it.

## Error handling boundary

Adapter-level error handling should remain minimal:
- one top-level try/except around pipeline invocation,
- rethrow as `AIPipelineUpstreamError` with original exception class/message in details,
- avoid implementing provider/model-specific fallback logic in route files.

## Why this contract exists

Historically, route and utility code started to duplicate model parsing/normalization behavior. That caused divergence from module behavior and harder debugging. This contract keeps responsibilities clear:

- API/routes: validate payload shape + auth + persistence,
- resolver: choose provider/model source,
- pipeline module: load model, interpret model id, invoke generation.
