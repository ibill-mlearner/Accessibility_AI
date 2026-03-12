# Step 2 — User prompt and message resolution

## Purpose

Resolve the canonical user prompt text and preserve usable message history for provider context.

## Primary helper

- `build_prompt_and_messages(payload)`.

## Detailed logic levels

1. **Attempt direct prompt usage**
   - The helper reads `payload.prompt`.
   - If non-empty after trimming, this becomes the canonical prompt.

2. **Normalize message container**
   - Reads `payload.messages`.
   - If not a list, message history falls back to an empty list.

3. **Backfill prompt from messages when needed**
   - When `payload.prompt` is empty, the helper scans messages in reverse order.
   - It selects the newest valid `role=user` message with non-empty string content.

4. **Return pair for downstream flow**
   - Returns `(prompt, messages)` as the canonical prompt context pair.

## Inputs consumed in this step

- `payload.prompt`
- `payload.messages`

## Outputs produced in this step

- `prompt: str`
- `messages: list[dict[str, Any]]`

## Why this step matters for system prompt workflow

- System instructions are paired with this resolved prompt later.
- Prompt resolution consistency ensures provider calls receive predictable user intent even when clients omit explicit `payload.prompt`.
