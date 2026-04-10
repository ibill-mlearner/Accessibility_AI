# Step 7 — Gateway/provider packaging

## File → Method → Next method

- **File:** `AccessBackEnd/app/services/ai_pipeline_gateway.py`
- **Method:** `AIPipelineGateway.run_interaction(prompt, context, **kwargs)`
- **Calls next:** `AIPipelineGateway.run(..., system_content=kwargs.get("system_prompt"))`
- **Calls next:** provider adapter constructor `AIPipeline(..., system_content=resolved_system_content, prompt_value=prompt, ...)`

## What this step does (only)

1. Forwards composed `system_prompt` into `run(... system_content=...)`.
2. If missing, `run()` falls back to `_build_system_content()`.
3. `_build_system_content()` starts with `AI_SYSTEM_GUARDRAIL_PROMPT` and appends DB prompt text.
4. Sends `system_content` + `prompt_value` to the provider adapter.

## Output

- Provider request payload ready for generation.
