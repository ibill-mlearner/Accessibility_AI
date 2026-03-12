# Step 1 — Request payload parsing and validation

## Purpose

This step creates a safe, normalized input boundary before any prompt/system-instruction logic runs.

## Entry point and call chain

- Route: `POST /api/v1/ai/interactions`.
- Parser entry: `AIInteractionRequestParser.parse_payload()`.
- Validation schema: `AIInteractionPayloadSchema`.

## Detailed logic levels

1. **Raw request body read**
   - The parser reads a JSON object from the request.
   - Logging captures path and available keys for traceability.

2. **Schema validation pass**
   - The payload is validated against `AIInteractionPayloadSchema`.
   - Structural and type-level mismatches are rejected early.

3. **Failure path**
   - If schema validation fails, a `BadRequestError` path is triggered.
   - Validation failures are logged with request key context.

4. **Success path**
   - A validated payload is returned and used by downstream composition helpers.

## Inputs consumed in this step

- JSON payload submitted by caller.

## Outputs produced in this step

- A validated `payload: dict[str, object]` with known structure.

## Why this step matters for system prompt workflow

- Every downstream step (prompt extraction, DB instruction sourcing, and system prompt composition) depends on key presence and shape.
- Early schema rejection prevents composition helpers from operating on malformed input.
