import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "app" / "services")))
sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "app")))
sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "app" / "utils" / "ai_checker")))
from ai_pipeline_v2.service import AIPipelineService
from ai_pipeline_v2.types import AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError
from model_artifacts import has_valid_model_artifacts, local_model_dir, model_artifact_diagnostics


def test_run_uses_chat_messages_and_system_prompt():
    captured = {}

    class FakePipe:
        def __call__(self, messages, max_new_tokens=256):
            captured["messages"] = messages
            captured["max_new_tokens"] = max_new_tokens
            return [{"generated_text": [*messages, {"role": "assistant", "content": "answer"}]}]

    service = AIPipelineService(
        AIPipelineConfig(model_id="m", max_new_tokens=77),
        runtime_client_factory=lambda _cfg: FakePipe(),
    )

    result = service.run(
        AIPipelineRequest(
            prompt="",
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Be concise",
            context={"chat_id": 1},
            request_id="req-1",
        )
    )

    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][0]["content"] == "Be concise"
    assert captured["messages"][1]["content"] == "Hi"
    assert captured["max_new_tokens"] == 77
    assert result["assistant_text"] == "answer"
    assert result["meta"]["selected_provider"] == "huggingface"


def test_run_uses_canonical_runtime_model_id_for_invocation():
    invoked = {}

    class FakePipe:
        def __call__(self, messages, max_new_tokens=256):
            return [{"generated_text": [*messages, {"role": "assistant", "content": "ok"}]}]

    service = AIPipelineService(
        AIPipelineConfig(model_id="default/model"),
        runtime_client_factory=lambda _cfg: FakePipe(),
    )

    original_ensure_pipe = service._ensure_pipe

    def _capture(model_id):
        invoked["model_id"] = model_id
        return original_ensure_pipe(model_id)

    service._ensure_pipe = _capture

    result = service.run(
        AIPipelineRequest(
            prompt="hello",
            context={
                "runtime_model_selection": {
                    "provider": "huggingface",
                    "model_id": "huggingfacetb/smollm-135m-instruct",
                }
            },
        )
    )

    assert invoked["model_id"] == "huggingfacetb/smollm-135m-instruct"
    assert result["meta"]["selected_model_id"] == "huggingfacetb/smollm-135m-instruct"


def test_pipeline_can_send_prompt_after_instantiation():
    class FakePipe:
        def __call__(self, messages, max_new_tokens=256):
            user_msg = messages[-1]["content"]
            return [{"generated_text": [*messages, {"role": "assistant", "content": f"echo:{user_msg}"}]}]

    service = AIPipelineService(AIPipelineConfig(model_id="m"), runtime_client_factory=lambda _cfg: FakePipe())
    result = service.run_interaction("hello world")
    assert result["assistant_text"] == "echo:hello world"


def test_runtime_error_raises_upstream_error():
    class FakePipe:
        def __call__(self, messages, max_new_tokens=256):
            raise RuntimeError("upstream auth failed")

    service = AIPipelineService(AIPipelineConfig(model_id="m"), runtime_client_factory=lambda _cfg: FakePipe())

    with pytest.raises(AIPipelineUpstreamError, match="Model invocation failed"):
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
            model_id=str(model_dir),
            max_new_tokens=64,
        )
    )

    result = service.run_interaction(_MODEL_TEST_PROMPT)

    assert isinstance(result["assistant_text"], str)
    assert result["assistant_text"].strip()
    assert result["meta"]["selected_model_id"] == str(model_dir)


def test_ensure_pipe_uses_dtype_kwarg_and_skips_device_map_without_accelerate(monkeypatch):
    captured = {}

    def fake_pipeline(task, model=None, **kwargs):
        captured["task"] = task
        captured["model"] = model
        captured["kwargs"] = kwargs

        class _Pipe:
            def __call__(self, messages, max_new_tokens=256):
                return [{"generated_text": [*messages, {"role": "assistant", "content": "ok"}]}]

        return _Pipe()

    from ai_pipeline_v2 import service as service_module

    monkeypatch.setattr(service_module, "pipeline", fake_pipeline)
    monkeypatch.setattr(AIPipelineService, "_accelerate_available", staticmethod(lambda: False))

    service = AIPipelineService(AIPipelineConfig(model_id="repo/model", torch_dtype="bfloat16", device_map="auto"))

    service.run(AIPipelineRequest(prompt="hello"))

    assert captured["task"] == "text-generation"
    assert captured["model"] == "repo/model"
    assert "dtype" in captured["kwargs"]
    assert "torch_dtype" not in captured["kwargs"]
    assert "device_map" not in captured["kwargs"]


def test_ensure_pipe_passes_device_map_when_accelerate_available(monkeypatch):
    captured = {}

    def fake_pipeline(task, model=None, **kwargs):
        captured["kwargs"] = kwargs

        class _Pipe:
            def __call__(self, messages, max_new_tokens=256):
                return [{"generated_text": [*messages, {"role": "assistant", "content": "ok"}]}]

        return _Pipe()

    from ai_pipeline_v2 import service as service_module

    monkeypatch.setattr(service_module, "pipeline", fake_pipeline)
    monkeypatch.setattr(AIPipelineService, "_accelerate_available", staticmethod(lambda: True))

    service = AIPipelineService(AIPipelineConfig(model_id="repo/model", device_map="auto"))

    service.run(AIPipelineRequest(prompt="hello"))

    assert captured["kwargs"].get("device_map") == "auto"