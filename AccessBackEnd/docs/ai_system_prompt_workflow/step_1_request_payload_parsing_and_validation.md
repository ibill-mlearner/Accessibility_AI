# Step 1 — Request payload parsing and validation

## File → Method → Next method

- **File:** `AccessBackEnd/app/api/v1/ai_interactions_routes.py`
- **Method:** `create_ai_interaction()`
- **Calls next:** `prepare_interaction_inputs(payload)` in `AccessBackEnd/app/utils/ai_checker/operations.py`

## What this step does (only)

1. Reads JSON and validates shape (`_validate_interaction_payload`).
2. Hands a validated `payload` into `prepare_interaction_inputs(payload)`.

## Output

- `payload: dict` ready for prompt resolution.
