# Step 3 — Database-backed system instruction resolution

## Purpose

Build the DB-derived instruction bundle used as the accommodation-aware system context.

## Primary helper

- `_resolve_system_instructions(payload)`.

## Detailed logic levels

1. **Resolve accommodation-system-prompt link scope**
   - The helper asks `_resolve_prompt_link_id(payload)` for a selected link id.
   - If present, it loads the `AccommodationSystemPrompt` link record.

2. **Resolve class scope**
   - The helper asks `_resolve_class_id(payload)`.
   - Resolution priority:
     1. explicit `payload.class_id` if provided,
     2. class inferred from chat if `chat_id` is provided and class id is omitted,
     3. no class context if neither path resolves.

3. **Extract source text fragments**
   - From link + class records, it prepares these fragments:
     - `prompt_link.system_prompt.text`
     - `prompt_link.accommodation.details`
     - `class_record.description`

4. **Normalize each fragment**
   - Each candidate passes through shared text cleaning (`to_clean_text(...)`).
   - This removes low-quality formatting/noise before composition.

5. **Join non-empty fragments**
   - Empty fragments are skipped.
   - Remaining fragments are combined with blank-line separators.

## Inputs consumed in this step

- `payload` keys that identify prompt-link/class/chat scope.
- DB records reachable from selected IDs.

## Outputs produced in this step

- `system_instructions: str` (DB-derived instruction text, may be empty).

## Why this step matters for system prompt workflow

- This is the accommodation-aware personalization boundary.
- It ensures system guidance can reflect both selected accessibility settings and class framing before final system prompt composition.
