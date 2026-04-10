# Step 6 — Route-to-gateway runtime injection

## File → Method → Next method

- **File:** `AccessBackEnd/app/api/v1/ai_interactions_routes.py`
- **Method:** `_run(ai_service, payload, prepared, chat_id, initiated_by)`
- **Called by:** `create_ai_interaction()`
- **Calls next:** `AIPipelineGateway.run_interaction(...)`

## What this step does (only)

1. Adds runtime model selection onto `prepared["context_payload"]`.
2. Calls `ai_service.run_interaction(...)` with:
   - `prepared["prompt"]`
   - `prepared["messages"]`
   - `prepared["system_prompt"]`
   - `prepared["context_payload"]`

## Output

- Normalized provider response.
