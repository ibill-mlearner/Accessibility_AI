# Services Runtime Workflow Guide

This README documents the **current backend services workflow** after the recent cleanup work.

## What changed (high level)

The service layer now reflects three major workflow cleanups:

1. **Config resolution cleanup**
   - Service-adjacent config parsing moved toward shared helpers and module-owned typed contracts.
   - Startup now resolves module config once, reducing repeated environment/config lookups.

2. **AI model inventory and catalog cleanup**
   - Model inventory fetches now support bounded parallel provider probes.
   - Inventory cache behavior is explicitly TTL-driven via `AI_INVENTORY_CACHE_TTL_SECONDS`.
   - Catalog responses include timing metadata for easier diagnostics.

3. **Gateway + bootstrap wiring cleanup**
   - The app bootstrap wires the AI service through `AIPipelineGateway`.
   - Runtime model selection and system-prompt composition remain centralized in the gateway path.
   - Logging bootstrap wraps the AI service with interaction logging without changing call sites.

---

## End-to-end service flow

### 1) App bootstrap
- `create_app(...)` initializes core extensions.
- AI service wiring resolves to `AIPipelineGateway` and is stored in `app.extensions["ai_service"]`.
- Logging bootstrap optionally wraps that service for interaction logging.

### 2) Request enters API routes
- API routes call `ai_service.run_interaction(...)`.
- Context may include runtime provider/model selection.

### 3) System prompt assembly
- Gateway composes final system content from:
  - `AI_SYSTEM_GUARDRAIL_PROMPT`
  - DB-backed system prompts
  - active accommodation prompt details

### 4) Runtime execution
- Gateway loads runtime module candidates (`ai_pipeline`, `ai_pipeline_thin...`).
- Model + tokenizer are built.
- Generation runs with configured token limits.
- Response payload includes assistant text and selection metadata.

### 5) Model catalog path
- Model list resolves from configured/default model + DB records.
- Catalog/inventory endpoints apply cache + provider probe behavior from cleaned-up inventory workflow.

---

## Key service modules

- `ai_pipeline_gateway.py`
  - Main orchestration entry point for AI prompt execution and model listing/download helpers.
- `logging/bootstrap.py`
  - Initializes logging, startup test runner hooks, and interaction-log wrapping.
- `logging/interaction_file_logger.py`
  - Writes interaction logs with rotating text file behavior.

---

## Operational notes

- If `ai_pipeline` runtime modules are unavailable, gateway calls will raise module import errors by design.
- `AI_SYSTEM_GUARDRAIL_PROMPT` is required for final system content assembly.
- `AI_INTERACTION_LOG_DIR` should be preferred over deprecated `DB_LOG_DIRECTORY`.

---

## Suggested follow-ups

- Add a short sequence diagram in this folder to visualize API → gateway → runtime → logging flow.
- Add a dedicated troubleshooting matrix for common runtime/module import failures.
- Keep this README synchronized whenever gateway contract fields or catalog timing metadata changes.
