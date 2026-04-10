# Step 5 — Prepared interaction payload packaging

## File → Method → Next method

- **File:** `AccessBackEnd/app/utils/ai_checker/operations.py`
- **Method:** `prepare_interaction_inputs(payload)`
- **Called by:** `create_ai_interaction()` route
- **Calls next:** `_run(...)` in `AccessBackEnd/app/api/v1/ai_interactions_routes.py`

## What this step does (only)

1. Calls `build_prompt_and_messages(payload)`.
2. Calls `build_context_and_system_instructions(payload, messages)`.
3. Calls `compose_system_prompt(system_instructions, payload)`.
4. Returns one dict with:
   - `prompt`
   - `messages`
   - `context_payload`
   - `system_prompt`
   - `request_id`

## Output

- `prepared: dict` used directly by the route.
