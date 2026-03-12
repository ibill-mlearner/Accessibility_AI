# Step 5 — Pipeline request DTO packaging

## Purpose

Package resolved prompt/system/context fields into a single transport object for pipeline execution.

## Primary assembly path

- `AIInteractionRequestParser.build_request_dto(payload)`
- DTO payload type: `AIPipelineRequest`

## Detailed logic levels

1. **Collect resolved prompt + messages**
   - Pulls output from `build_prompt_and_messages(payload)`.

2. **Collect resolved context + DB instructions**
   - Pulls output from `build_context_and_system_instructions(payload, messages)`.

3. **Collect composed system prompt**
   - Calls `compose_system_prompt(system_instructions, payload)`.

4. **Resolve cross-cutting metadata**
   - Resolves chat id, initiator identity, class/user ids, optional RAG payload, and request id.

5. **Construct `AIPipelineRequest`**
   - Key fields for prompt workflow:
     - `prompt`
     - `messages`
     - `system_prompt`
     - `context`

6. **Return wrapper DTO structure**
   - Returns additional diagnostic/context fields alongside the constructed pipeline request.

## Inputs consumed in this step

- Outputs of Steps 2–4
- Additional metadata from payload/session context

## Outputs produced in this step

- `AIPipelineRequest` ready for `ai_service.run(...)`

## Why this step matters for system prompt workflow

- It preserves boundaries between user prompt content, message history, and composed system instructions while still creating one execution-ready request object.
