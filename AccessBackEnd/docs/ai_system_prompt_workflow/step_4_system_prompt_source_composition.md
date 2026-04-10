# Step 4 — System prompt source composition

## File → Method → Next method

- **File:** `AccessBackEnd/app/utils/ai_checker/operations.py`
- **Method:** `compose_system_prompt(system_instructions, payload)`
- **Called by:** `prepare_interaction_inputs(payload)`
- **Calls next:** `AIPipelineGateway.run_interaction(..., system_prompt=prepared["system_prompt"])`

## What this step does (only)

1. Reads config `AI_SYSTEM_GUARDRAIL_PROMPT`.
2. Takes `system_instructions` from Step 3.
3. Reads `payload.system_prompt`.
4. Concatenates non-empty parts in fixed order:
   - guardrail
   - DB accessibility instructions
   - request-level system prompt
5. Returns composed prompt or `None`.

## Output

- `composed_system_prompt: str | None`
