# Step 2 — User prompt and message resolution

## File → Method → Next method

- **File:** `AccessBackEnd/app/utils/ai_checker/operations.py`
- **Method:** `build_prompt_and_messages(payload)`
- **Called by:** `prepare_interaction_inputs(payload)`
- **Calls next:** `build_context_and_system_instructions(payload, messages)`

## What this step does (only)

1. Reads `payload.prompt`.
2. Reads `payload.messages` (list or empty list).
3. If `prompt` is empty, backfills from the newest valid `role=user` message.
4. Returns `(prompt, messages)`.

## Output

- `prompt: str`
- `messages: list[dict]`
