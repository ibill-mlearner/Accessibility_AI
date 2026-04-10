# AI system prompt workflow

This index maps the current runtime call chain used in `POST /api/v1/ai/interactions`.

## Call chain at a glance

1. `create_ai_interaction()`
2. `prepare_interaction_inputs(payload)`
3. `build_prompt_and_messages(payload)`
4. `build_context_and_system_instructions(payload, messages)`
5. `AIInteractionOps._resolve_system_instructions(payload)`
6. `compose_system_prompt(system_instructions, payload)`
7. `_run(...)->AIPipelineGateway.run_interaction(...)->run(...)->AIPipeline(...)`

## Step-by-step files

1. `AccessBackEnd/docs/ai_system_prompt_workflow/step_1_request_payload_parsing_and_validation.md`
2. `AccessBackEnd/docs/ai_system_prompt_workflow/step_2_user_prompt_and_message_resolution.md`
3. `AccessBackEnd/docs/ai_system_prompt_workflow/step_3_db_backed_system_instruction_resolution.md`
4. `AccessBackEnd/docs/ai_system_prompt_workflow/step_4_system_prompt_source_composition.md`
5. `AccessBackEnd/docs/ai_system_prompt_workflow/step_5_pipeline_request_dto_packaging.md`
6. `AccessBackEnd/docs/ai_system_prompt_workflow/step_6_runtime_context_injection.md`
7. `AccessBackEnd/docs/ai_system_prompt_workflow/step_7_provider_specific_packaging.md`
