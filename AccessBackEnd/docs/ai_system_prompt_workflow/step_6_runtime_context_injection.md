# Step 6 — Runtime context injection before provider invocation

## Purpose

Map composed prompt fields into runtime context used by provider adapters.

## Primary execution path

- `AIPipelineService.run(request)`.

## Detailed logic levels

1. **Resolve prompt fallback defensively**
   - Pipeline re-resolves prompt (`_resolve_prompt`) in case upstream input was incomplete.

2. **Clone/normalize context object**
   - Uses a mutable context copy to avoid side effects on caller-provided objects.

3. **Inject request id when absent**
   - Adds `context["request_id"]` for traceability if not already present.

4. **Inject messages when absent**
   - Adds `context["messages"] = request.messages` if available and not already set.

5. **Inject composed system instructions**
   - If `request.system_prompt` exists, writes it to `context["system_instructions"]`.

6. **Invoke selected provider with prompt + context**
   - Calls provider invocation path with the canonical prompt and enriched runtime context.

## Inputs consumed in this step

- `AIPipelineRequest` fields (`prompt`, `messages`, `system_prompt`, `context`)

## Outputs produced in this step

- Provider-ready runtime context with composed system instructions attached.

## Why this step matters for system prompt workflow

- It is the handoff boundary between composition logic and transport logic.
- Provider adapters depend on `context["system_instructions"]` being present and pre-composed.
