# AI system prompt workflow

This document is the index for the system prompt workflow.

Per your request, each workflow step has its **own dedicated file** with deeper logic detail.

## Step-by-step deep-dive files

1. **Step 1 — Request payload parsing and validation**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_1_request_payload_parsing_and_validation.md`
2. **Step 2 — User prompt and message resolution**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_2_user_prompt_and_message_resolution.md`
3. **Step 3 — DB-backed system instruction resolution**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_3_db_backed_system_instruction_resolution.md`
4. **Step 4 — System prompt source composition**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_4_system_prompt_source_composition.md`
5. **Step 5 — Pipeline request DTO packaging**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_5_pipeline_request_dto_packaging.md`
6. **Step 6 — Runtime context injection before provider invocation**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_6_runtime_context_injection.md`
7. **Step 7 — Provider-specific packaging of user + system content**
   `AccessBackEnd/docs/ai_system_prompt_workflow/step_7_provider_specific_packaging.md`

## Recommended reading order

Read steps in numeric order. If debugging specific issues, jump directly:

- **Missing or incorrect accommodation/class instruction text** → Step 3
- **Unexpected merged system prompt content/order** → Step 4
- **Prompt appears correct in parser but different at provider boundary** → Steps 5–7
