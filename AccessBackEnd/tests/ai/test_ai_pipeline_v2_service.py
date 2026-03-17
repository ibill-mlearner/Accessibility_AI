import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "app" / "services")))
sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "app")))
sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "app" / "utils" / "ai_checker")))
from ai_pipeline_v2.service import AIPipeline, AIPipelineService
from ai_pipeline_v2.types import AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError
from model_artifacts import (
    has_valid_model_artifacts,
    local_model_dir,
    model_artifact_diagnostics,
)



def test_run_normalizes_payload_and_context():
    calls = []

    class RuntimeClient:
        def invoke(self, prompt, context):
            calls.append({"prompt": prompt, "context": context})
            return {"response": "answer", "confidence": 0.8, "notes": "single", "meta": {"trace": "x"}}

        def health(self):
            return {"ok": True}

        def inventory(self):
            return []

        def name(self):
            return "local"

    service = AIPipelineService(AIPipelineConfig(model_name="m"), runtime_client=RuntimeClient())

    result = service.run(
        AIPipelineRequest(
            prompt="",
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Be concise",
            context={"chat_id": 1},
            request_id="req-1",
        )
    )

    assert calls[0]["prompt"] == "Hi"
    assert calls[0]["context"]["request_id"] == "req-1"
    assert calls[0]["context"]["system_instructions"] == "Be concise"
    assert result["assistant_text"] == "answer"
    assert result["notes"] == ["single"]
    assert result["meta"]["pipeline"] == "app.services.ai_pipeline_v2"




def test_minimal_pipeline_object_usage_contract(monkeypatch):
    class RuntimeClient:
        def invoke(self, prompt, context):
            return {"assistant_text": f"ok:{prompt}"}

        def health(self):
            return {"ok": True}

        def inventory(self):
            return []

        def name(self):
            return "local"

    ai_object = AIPipeline()
    monkeypatch.setattr(ai_object, "_get_runtime_client", lambda _model_id: RuntimeClient())

    response = ai_object.AIPipelineRequest("hello", {})

    assert response["assistant_text"] == "ok:hello"

def test_pipeline_can_send_prompt_after_instantiation():
    class RuntimeClient:
        def invoke(self, prompt, context):
            return {"assistant_text": f"echo:{prompt}"}

        def health(self):
            return {"ok": True}

        def inventory(self):
            return []

        def name(self):
            return "local"

    service = AIPipelineService(AIPipelineConfig(model_name="m"), runtime_client=RuntimeClient())
    result = service.run_interaction("hello world")
    assert result["assistant_text"] == "echo:hello world"


def test_runtime_selection_caches_client_by_model():
    created = []

    class RuntimeClient:
        def __init__(self, model):
            self.model = model

        def invoke(self, prompt, context):
            return {"assistant_text": f"{self.model}:{prompt}"}

        def health(self):
            return {"ok": True}

        def inventory(self):
            return []

        def name(self):
            return "local"

    def runtime_factory(config, *, model_id):
        created.append(model_id)
        return RuntimeClient(model_id)

    service = AIPipelineService(AIPipelineConfig(model_name="default"), runtime_client_factory=runtime_factory)

    request = AIPipelineRequest(prompt="hello", context={"runtime_model_selection": {"model_id": "model-A"}})
    first = service.run(request)
    second = service.run(request)

    assert first["assistant_text"] == "model-A:hello"
    assert second["assistant_text"] == "model-A:hello"
    assert len(created) == 1
    assert created[0] == "model-A"


def test_runtime_error_returns_runtime_unavailable():
    class RuntimeClient:
        def invoke(self, prompt, context):
            raise RuntimeError("local runtime bootstrap failed")

        def health(self):
            return {"ok": False}

        def inventory(self):
            return []

        def name(self):
            return "local"

    service = AIPipelineService(AIPipelineConfig(model_name="model-x"), runtime_client=RuntimeClient())

    with pytest.raises(AIPipelineUpstreamError) as exc_info:
        service.run(AIPipelineRequest(prompt="help"))

    details = exc_info.value.details if isinstance(exc_info.value.details, dict) else {}
    assert details.get("error_code") == "runtime_unavailable"
    assert details.get("model_id") == "model-x"


def test_non_fallback_error_raises_upstream_error():
    class RuntimeClient:
        def invoke(self, prompt, context):
            raise RuntimeError("upstream auth failed")

        def health(self):
            return {"ok": False}

        def inventory(self):
            return []

        def name(self):
            return "local"

    service = AIPipelineService(AIPipelineConfig(model_name="m"), runtime_client=RuntimeClient())

    with pytest.raises(AIPipelineUpstreamError, match=r"There was a problem with the model contact the administrator\."):
        service.run(AIPipelineRequest(prompt="hello"))


def test_model_artifact_validator_detects_valid_and_invalid_layout(tmp_path: Path):
    invalid_dir = tmp_path / "invalid-model"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    (invalid_dir / "config.json").write_text("{}", encoding="utf-8")
    assert has_valid_model_artifacts(invalid_dir) is False

    valid_dir = tmp_path / "valid-model"
    valid_dir.mkdir(parents=True, exist_ok=True)
    (valid_dir / "config.json").write_text('{"model_type":"qwen2"}', encoding="utf-8")
    (valid_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (valid_dir / "model.safetensors.index.json").write_text("{}", encoding="utf-8")
    assert has_valid_model_artifacts(valid_dir) is True


_SMALL_MODEL_IDS = (
    "Qwen/Qwen2.5-0.5B-Instruct",
    "HuggingFaceTB/SmolLM2-360M-Instruct",
    "HuggingFaceTB/SmolLM-135M-Instruct",
)
_MODEL_TEST_PROMPT = "Reply with one short sentence confirming you are running."


def _ensure_local_model_artifacts(model_dir: Path, model_id: str, transformers) -> None:
    if has_valid_model_artifacts(model_dir):
        return
    model_dir.mkdir(parents=True, exist_ok=True)
    try:
        tokenizer = transformers.AutoTokenizer.from_pretrained(model_id)
        model = transformers.AutoModelForCausalLM.from_pretrained(model_id)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Unable to download {model_id} in this environment: {exc}")
    tokenizer.save_pretrained(model_dir)
    model.save_pretrained(model_dir)


@pytest.mark.parametrize("model_id", _SMALL_MODEL_IDS)
def test_pipeline_with_local_small_models_returns_response(model_id: str):
    project_root = Path(__file__).resolve().parents[2]
    configured_model = str(os.getenv("AI_MODEL_NAME") or "").strip()
    model_dir = Path(configured_model).expanduser().resolve() if configured_model else local_model_dir(project_root, model_id)

    transformers = pytest.importorskip("transformers", reason="transformers is required for local model download/inference")
    _ensure_local_model_artifacts(model_dir, model_id, transformers)

    if not has_valid_model_artifacts(model_dir):
        diagnostics = model_artifact_diagnostics(model_dir)
        pytest.fail(
            "Local model artifacts are invalid after download attempt. "
            f"model_id={model_id} "
            f"resolved_model_dir={diagnostics['resolved_model_dir']} "
            f"exists={diagnostics['exists']} "
            f"is_dir={diagnostics['is_dir']} "
            f"config_json_exists={diagnostics['config_json_exists']} "
            f"config_json_parseable={diagnostics['config_json_parseable']} "
            f"config_model_type_present={diagnostics['config_model_type_present']} "
            f"tokenizer_files_present={diagnostics['tokenizer_files_present']} "
            f"tokenizer_files_found={diagnostics['tokenizer_files_found']} "
            f"weight_files_present={diagnostics['weight_files_present']} "
            f"weight_files_found={diagnostics['weight_files_found']} "
            f"directory_listing={diagnostics['directory_listing']}"
        )

    service = AIPipelineService(
        AIPipelineConfig(
            model_name=str(model_dir),
            timeout_seconds=120,
            max_new_tokens=64,
        ),

    )

    result = service.run_interaction(_MODEL_TEST_PROMPT)

    assert isinstance(result["assistant_text"], str)
    assert result["assistant_text"].strip()
    assert result["meta"]["selected_model_id"] == str(model_dir)
