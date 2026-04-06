import ai_pipeline
import importlib.util


def _accelerate_available() -> bool:
    return importlib.util.find_spec("accelerate") is not None


def run_single(prompt: str) -> None:
    pipeline = ai_pipeline.AIPipeline(
        model_name_value="HuggingFaceTB/SmolLM2-360M-Instruct",
        system_content="You are a concise assistant.",
        prompt_value=prompt,
        download_locally=True,
    )

    if _accelerate_available():
        pipeline.model_loader.device_map = "auto"
    else:
        pipeline.model_loader.device_map = None
    if hasattr(pipeline.model_loader, "dtype"):
        pipeline.model_loader.dtype = "auto"
    else:
        pipeline.model_loader.torch_dtype = "auto"

    model = pipeline.build_model()
    tokenizer = pipeline.build_tokenizer()

    text = pipeline.build_text(tokenizer=tokenizer)
    model_inputs = pipeline.build_model_inputs(
        tokenizer=tokenizer,
        text=text,
        model=model,
    )

    raw_ids = pipeline.build_raw_generated_ids(
        model=model,
        model_inputs=model_inputs,
        max_new_tokens=100,
    )

    generated_ids = pipeline.build_generated_ids(
        model_inputs=model_inputs,
        raw_generated_ids=raw_ids,
    )

    response = pipeline.build_response(
        tokenizer=tokenizer,
        generated_ids=generated_ids,
    )

    print(response)


if __name__ == "__main__":
    run_single("Explain what an AI pipeline is in 2 sentences.")
