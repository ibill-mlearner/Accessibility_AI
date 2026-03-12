# Step 4 — System prompt source composition

## Purpose

Merge all system-side instruction sources into one composed value used by pipeline execution.

## Primary helper

- `compose_system_prompt(system_instructions, payload)`.

## Detailed logic levels

1. **Read global guardrail source**
   - Reads `AI_SYSTEM_GUARDRAIL_PROMPT` from app config.
   - Trims whitespace and keeps empty as optional.

2. **Receive DB-sourced instructions**
   - Accepts `system_instructions` from Step 3.
   - Treats missing/empty as optional.

3. **Read request-scoped system prompt**
   - Reads `payload.system_prompt`.
   - Trims whitespace and keeps empty as optional.

4. **Compose ordered parts**
   - Source order is fixed to:
     1. global guardrail,
     2. DB instructions,
     3. request-level overlay.

5. **Join non-empty parts**
   - Uses blank-line separators for readability and boundary clarity.
   - Returns `None` only when all sources are empty.

## Inputs consumed in this step

- `AI_SYSTEM_GUARDRAIL_PROMPT`
- `system_instructions`
- `payload.system_prompt`

## Outputs produced in this step

- `composed_system_prompt: str | None`

## Why this step matters for system prompt workflow

- It centralizes policy composition in one function.
- It prevents providers from re-implementing merge logic and drifting over time.
