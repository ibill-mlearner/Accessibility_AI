# Step 3 — DB-backed accessibility instruction resolution

## File → Method → Next method

- **File:** `AccessBackEnd/app/utils/ai_checker/operations.py`
- **Method:** `AIInteractionOps._resolve_system_instructions(payload)`
- **Called by:** `build_context_and_system_instructions(payload, messages)`
- **Calls next:** `compose_system_prompt(system_instructions, payload)`

## What this step does (only)

1. Reads `payload.selected_accessibility_link_ids` and normalizes ids.
2. Pulls matching `UserAccessibilityFeature -> accommodation.details` text.
3. If none found, falls back to `_resolve_prompt_link_id(payload)` and `AccommodationSystemPrompt -> accommodation.details`.
4. Returns a single joined string.

## Output

- `system_instructions: str`
