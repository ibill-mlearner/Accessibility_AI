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

## Hardware readiness and model runtime checklist

Use this checklist before enabling larger local models (for example 8B class models):

1. **CPU-only minimum baseline**
   - Start with `AI_PROVIDER=ollama` and a smaller model id in `AI_OLLAMA_MODEL`.
   - Verify latency and response shape at `/api/v1/ai/interactions`.
2. **GPU capability checks (if available)**
   - Confirm CUDA/ROCm visibility from the host before app startup.
   - Validate VRAM against selected model size + context length targets.
3. **Model availability checks**
   - For Ollama: ensure model is pulled and appears in `/api/tags`.
   - For Hugging Face local mode: ensure `AI_MODEL_NAME` points to an existing local model directory or `AI_HUGGINGFACE_CACHE_DIR` is pre-populated.
4. **Provider health checks**
   - Use `GET /api/v1/ai/catalog` and inspect `provider_health` in the response.
   - Use `GET /api/v1/ai/models/available` to verify discoverability.
5. **Runtime fallback policy**
   - Keep a known-fast small model configured as default for degraded hardware conditions.
   - Use per-session `/api/v1/ai/selection` overrides for opt-in larger models.

### Suggested pipeline extension points for hardware-aware routing

- Add a `hardware_probe` module under `app/services/ai_pipeline/` that returns a normalized snapshot:
  - CPU core count
  - available system memory
  - GPU vendor/name/count
  - free/total VRAM
- Run this probe during `build_ai_service_from_config(...)` and cache the snapshot in app extensions.
- Extend model selection to reject or warn on models that exceed hardware thresholds.
- Persist probe snapshots in logs/telemetry so model performance incidents can be correlated with hardware state.

## Accessibility feature persistence plan (next step)

Current behavior: selected accessibility links are request-scoped and primarily feed front-end options. To persist user preferences across sessions, add a relational join table between users and accessibility features.

Proposed schema shape:

- `user_accessibility_feature_preferences`
  - `id` (PK)
  - `user_id` (FK -> users.id)
  - `accessibility_feature_id` (FK -> accommodations/accessibility feature table)
  - `enabled` (boolean)
  - `updated_at` (timestamp)
  - unique constraint: (`user_id`, `accessibility_feature_id`)

Integration points:

1. Read enabled features on session/bootstrap and hydrate UI defaults.
2. Include enabled feature ids in AI interaction payload composition when explicit selections are absent.
3. Keep system prompt link resolution (`selected_accessibility_link_ids` -> accommodation prompt link) unchanged, but source ids from persisted preferences by default.
4. Add APIs for preference upsert/remove and keep them independent from the feature catalog endpoint.
