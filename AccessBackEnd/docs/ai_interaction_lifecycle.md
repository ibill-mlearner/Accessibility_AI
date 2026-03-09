# AI interaction request lifecycle (current implementation)

## Endpoint flow

`POST /api/v1/ai/interactions` (`app/api/v1/ai_interactions_routes.py`) processes a request in the following sequence:

1. Parse and validate payload with `AIInteractionPayloadSchema`.
2. Normalize prompt/messages/context in-route:
   - prefer `payload.prompt`
   - otherwise backfill prompt from latest user message
   - attach `messages` into `context` when absent
3. Resolve database-backed system instructions from selected accommodation/system-prompt link.
4. Resolve `ai_service = current_app.extensions["ai_service"]` and build `AIPipelineRequest`.
5. Call `ai_service.run(dto)`.
6. `AIPipelineService.run()` (`app/services/ai_pipeline/pipeline.py`) executes:
   - `_resolve_prompt(request)`
   - context normalization and system instruction injection
   - `invoke_provider_or_raise(self._provider, prompt, context)`
   - provider payload normalization into `assistant_text`, `confidence`, `notes`, `meta`
7. API route performs final normalization (`_normalize_interaction_response`), persists interaction, and returns JSON to the UI.

## Provider selection/invocation config keys

The provider path uses the following config keys in `build_ai_service_from_config(...)` and provider factory wiring:

- `AI_PROVIDER`
- `AI_MODEL_NAME`
- `AI_TIMEOUT_SECONDS`
- `AI_OLLAMA_ENDPOINT`
- `AI_OLLAMA_MODEL`
- `AI_OLLAMA_OPTIONS`
- `AI_LIVE_ENDPOINT`

For the Hugging Face provider, `AI_MODEL_NAME` is forwarded as `huggingface_model_id`.

## POC local-only model policy (current)

- Dynamic Hugging Face Hub downloads are disabled by default for the POC (`AI_HUGGINGFACE_ALLOW_DOWNLOAD=false`).
- The pipeline now expects developer-preloaded local models only:
  - either set `AI_MODEL_NAME` to a local filesystem path
  - or pre-populate `AI_HUGGINGFACE_CACHE_DIR` with cached snapshots.
- This keeps runtime deterministic and avoids Hub auth/gated-model failures during local development.
