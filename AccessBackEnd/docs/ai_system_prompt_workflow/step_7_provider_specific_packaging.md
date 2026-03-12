# Step 7 — Provider-specific packaging of user + system content

## Purpose

Transform canonical prompt/context inputs into the wire format required by each provider.

## Scope

This step does **not** re-compose system prompt sources. It only transports the already composed `context["system_instructions"]`.

## Detailed logic levels

### A) Ollama provider packaging

1. Build chat `messages` payload with explicit roles.
2. Include a baseline assistant contract as a system message.
3. Include composed `context["system_instructions"]` as a system message when present.
4. Include resolved user prompt as a user message.
5. Optionally append context summary as another system message.

Result:
- System and user content are sent as separate role messages.

### B) Hugging Face provider packaging

1. Build a text template with named sections.
2. Inject composed system instructions into `System instructions section`.
3. Inject resolved user prompt into `User prompt`.
4. Inject context summary + output contract fields.

Result:
- System and user content are delivered inside one rendered prompt template.

## Inputs consumed in this step

- `prompt`
- `context["system_instructions"]`
- optional context metadata/messages

## Outputs produced in this step

- Provider-specific request payload/body.

## Why this step matters for system prompt workflow

- It preserves one composition source of truth while allowing transport-level differences across providers.
