from __future__ import annotations

import importlib

import pytest


def _load_ai_pipeline_module():
    candidates = (
        "ai_pipeline_thin.ai_pipeline",
        "app.services.ai_pipeline_thin.ai_pipeline",
        "AccessBackEnd.app.services.ai_pipeline_thin.ai_pipeline",
    )
    for module_path in candidates:
        try:
            return importlib.import_module(module_path)
        except ModuleNotFoundError:
            continue
    pytest.skip("could not import ai pipeline module from known project paths")


LOW_PARAMETER_MODEL_IDS = (
    "Qwen/Qwen2.5-0.5B-Instruct",
    "HuggingFaceTB/SmolLM2-360M-Instruct",
    "Qwen/Qwen2.5-0.5B",
)


@pytest.mark.parametrize("model_name", LOW_PARAMETER_MODEL_IDS)
def test_pipeline_runs_with_low_parameter_model_names(model_name: str):
    """Direct pipeline probe using demo.py flow across several small models."""
    ai_pipeline = _load_ai_pipeline_module()

    pipeline = ai_pipeline.AIPipeline(
        model_name_value=model_name,
        system_content="You are a concise assistant.",
        prompt_value="Write one short sentence about chicken noodle soup.",
        download_locally=True,
    )

    pipeline.model_loader.device_map = "auto"
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

    assert isinstance(response, str)
    assert response.strip() != ""
