import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "app" / "services")))
from app.services.ai_pipeline_v2.factory import create_provider
from app.services.ai_pipeline_v2.service import AIPipelineService
from app.services.ai_pipeline_v2.types import AIPipelineConfig, AIPipelineRequest, AIPipelineUpstreamError


_WEIGHT_CANDIDATES = (
    "pytorch_model.bin",
    "model.safetensors",
    "pytorch_model.bin.index.json",
    "model.safetensors.index.json",
)
_TOKENIZER_CANDIDATES = ("tokenizer.json", "tokenizer_config.json")


def model_artifact_diagnostics(path: Path) -> dict[str, object]:
    config_file = path / "config.json"
    diagnostics: dict[str, object] = {
        "resolved_model_dir": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "config_json_exists": config_file.exists(),
        "config_json_parseable": False,
        "config_model_type_present": False,
        "tokenizer_files_present": False,
        "tokenizer_files_found": [],
        "weight_files_present": False,
        "weight_files_found": [],
        "directory_listing": [],
    }

    if path.exists() and path.is_dir():
        diagnostics["directory_listing"] = sorted(child.name for child in path.iterdir())[:20]

    if config_file.exists() and config_file.is_file():
        try:
            config_payload = json.loads(config_file.read_text(encoding="utf-8"))
            diagnostics["config_json_parseable"] = isinstance(config_payload, dict)
            diagnostics["config_model_type_present"] = isinstance(config_payload, dict) and bool(config_payload.get("model_type"))
        except Exception:  # noqa: BLE001
            diagnostics["config_json_parseable"] = False

    found_tokenizers = [name for name in _TOKENIZER_CANDIDATES if (path / name).exists()]
    diagnostics["tokenizer_files_found"] = found_tokenizers
    diagnostics["tokenizer_files_present"] = bool(found_tokenizers)

    found_weights = [name for name in _WEIGHT_CANDIDATES if (path / name).exists()]
    diagnostics["weight_files_found"] = found_weights
    diagnostics["weight_files_present"] = bool(found_weights)
    return diagnostics


def has_valid_model_artifacts(path: Path) -> bool:
    info = model_artifact_diagnostics(path)
    return bool(
        info["exists"]
        and info["is_dir"]
        and info["config_json_exists"]
        and info["config_json_parseable"]
        and info["config_model_type_present"]
        and info["tokenizer_files_present"]
        and info["weight_files_present"]
    )


class DummyProvider:
    def __init__(self, payload=None, health_payload=None, models=None):
        self.payload = payload if payload is not None else {"assistant_text": "ok"}
        self.health_payload = health_payload if health_payload is not None else {"ok": True}
        self.models = models if models is not None else []
        self.calls = []

    def invoke(self, prompt, context):
        self.calls.append({"prompt": prompt, "context": context})
        return self.payload

    def health(self):
        return self.health_payload

    def inventory(self):
        return self.models

    def name(self):
        return "dummy"


def test_run_normalizes_payload_and_context():
    provider = DummyProvider(payload={"response": "answer", "confidence": 0.8, "notes": "single", "meta": {"trace": "x"}})
    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="m", ollama_model_id="m"),
        provider=provider,
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

    assert provider.calls[0]["prompt"] == "Hi"
    assert provider.calls[0]["context"]["request_id"] == "req-1"
    assert provider.calls[0]["context"]["system_instructions"] == "Be concise"
    assert result["assistant_text"] == "answer"
    assert result["notes"] == ["single"]
    assert result["meta"]["pipeline"] == "app.services.ai_pipeline_v2"


def test_runtime_selection_uses_cached_provider():
    created = []

    class RuntimeProvider(DummyProvider):
        def __init__(self, name, model):
            super().__init__({"assistant_text": f"{name}:{model}"})

    def provider_factory(config, *, provider, model_id):
        created.append((provider, model_id))
        return RuntimeProvider(provider, model_id)

    service = AIPipelineService(
        AIPipelineConfig(provider="ollama", model_name="default", ollama_model_id="default"),
        provider_factory=provider_factory,
    )

    request = AIPipelineRequest(prompt="hello", context={"runtime_model_selection": {"provider": "huggingface", "model_id": "hf-1"}})
    first = service.run(request)
    second = service.run(request)

    assert first["assistant_text"] == "huggingface:hf-1"
    assert second["assistant_text"] == "huggingface:hf-1"
    assert created == [("huggingface", "hf-1")]


def test_hf_error_falls_back_to_ollama():
    class HF:
        def invoke(self, prompt, context):
            raise RuntimeError("HuggingFace dynamic download is disabled in local-only mode")

        def health(self):
            return {"ok": False}

        def inventory(self):
            return []

        def name(self):
            return "huggingface"

    ollama = DummyProvider({"assistant_text": "fallback"})

    def provider_factory(config, *, provider, model_id):
        if provider == "huggingface":
            return HF()
        return ollama

    service = AIPipelineService(
        AIPipelineConfig(
            provider="huggingface",
            model_name="hf-model",
            huggingface_model_id="hf-model",
            ollama_model_id="ollama-model",
            enable_ollama_fallback_on_hf_local_only_error=True,
        ),
        provider_factory=provider_factory,
    )

    result = service.run(AIPipelineRequest(prompt="help"))
    assert result["assistant_text"] == "fallback"
    assert result["meta"]["fallback_to"] == "ollama"


def test_non_fallback_error_raises_upstream_error():
    class BadProvider(DummyProvider):
        def invoke(self, prompt, context):
            raise RuntimeError("upstream auth failed")

    service = AIPipelineService(
        AIPipelineConfig(provider="huggingface", model_name="hf", huggingface_model_id="hf"),
        provider=BadProvider(),
    )

    with pytest.raises(AIPipelineUpstreamError, match="upstream auth failed"):
        service.run(AIPipelineRequest(prompt="hello"))


def test_model_artifact_validator_detects_valid_and_invalid_layout(tmp_path: Path):
    invalid_dir = tmp_path / "invalid-model"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    (invalid_dir / "config.json").write_text(json.dumps({"model_type": "qwen2"}), encoding="utf-8")
    assert has_valid_model_artifacts(invalid_dir) is False

    valid_dir = tmp_path / "valid-model"
    valid_dir.mkdir(parents=True, exist_ok=True)
    (valid_dir / "config.json").write_text(json.dumps({"model_type": "qwen2"}), encoding="utf-8")
    (valid_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (valid_dir / "model.safetensors.index.json").write_text("{}", encoding="utf-8")
    assert has_valid_model_artifacts(valid_dir) is True


def test_pipeline_with_local_qwen_0_5b_model_returns_response():
    configured_model = str(os.getenv("AI_MODEL_NAME") or "").strip()
    project_root = Path(__file__).resolve().parents[2]
    default_model_dir = project_root / "instance" / "models" / "Qwen2.5-0.5B-Instruct"
    if configured_model:
        configured_path = Path(configured_model).expanduser()
        model_dir = configured_path if configured_path.is_absolute() else (project_root / configured_path)
    else:
        model_dir = default_model_dir
    model_dir = model_dir.resolve()

    transformers = pytest.importorskip("transformers", reason="transformers is required for local model download/inference")

    if not has_valid_model_artifacts(model_dir):
        model_dir.mkdir(parents=True, exist_ok=True)
        model_id = "Qwen/Qwen2.5-0.5B-Instruct"
        tokenizer = transformers.AutoTokenizer.from_pretrained(model_id)
        model = transformers.AutoModelForCausalLM.from_pretrained(model_id)
        tokenizer.save_pretrained(model_dir)
        model.save_pretrained(model_dir)

    if not has_valid_model_artifacts(model_dir):
        diagnostics = model_artifact_diagnostics(model_dir)
        pytest.fail(
            "Local model artifacts are invalid after download attempt. "
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
            provider="huggingface",
            model_name=str(model_dir),
            huggingface_model_id=str(model_dir),
            huggingface_allow_download=False,
            timeout_seconds=120,
            max_new_tokens=64,
        ),
        provider_factory=create_provider,
    )

    result = service.run(
        AIPipelineRequest(
            prompt="Reply with one short sentence confirming you are running.",
            request_id="qwen-0.5b-local-integration-test",
        )
    )

    assert isinstance(result["assistant_text"], str)
    assert result["assistant_text"].strip()
    assert result["meta"]["selected_provider"] == "huggingface"
    assert result["meta"]["selected_model_id"] == str(model_dir)
