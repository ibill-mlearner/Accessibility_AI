from pathlib import Path

from AccessBackEnd.app.services.ai_pipeline_v2.config import AIPipelineV2ModuleConfig
from AccessBackEnd.app.services.ai_pipeline_v2.factory import build_ai_service_from_config


class _DummyPipe:
    def __call__(self, messages, max_new_tokens=256):
        return [{"generated_text": [*messages, {"role": "assistant", "content": "ok"}]}]


def _dummy_pipe_factory(_config):
    return _DummyPipe()


def _base_module_config(**overrides):
    config = AIPipelineV2ModuleConfig(
        provider="huggingface",
        model_name="meta-llama/Llama-3.2-3B-Instruct",
        timeout_seconds=60,
        max_new_tokens=128,
        temperature=0.3,
        torch_dtype="bfloat16",
        device_map="auto",
        config_log_path="ai_pipeline_v2_model_config.txt",
        ollama_endpoint="",
        ollama_model_id="",
        ollama_options=None,
        live_endpoint="",
        huggingface_cache_dir=None,
        enable_ollama_fallback=True,
        inventory_cache_ttl_seconds=10,
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_build_ai_service_uses_repo_model_id_and_pipeline_params(tmp_path: Path):
    module_config = _base_module_config(
        model_name="Qwen/Qwen2.5-0.5B-Instruct",
        max_new_tokens=64,
        temperature=0.2,
        config_log_path=str(tmp_path / "model_config.txt"),
    )

    service = build_ai_service_from_config(module_config, runtime_client_factory=_dummy_pipe_factory)

    assert service.config.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert service.config.max_new_tokens == 64
    assert service.config.temperature == 0.2


def test_build_ai_service_mapping_transition_accepts_huggingface_repo_id(tmp_path: Path):
    service = build_ai_service_from_config(
        config={
            "AI_PROVIDER": "huggingface",
            "AI_MODEL_NAME": "Qwen/Qwen2.5-0.5B-Instruct",
            "AI_MAX_NEW_TOKENS": 32,
            "AI_TEMPERATURE": 0.1,
            "AI_CONFIG_LOG_PATH": str(tmp_path / "map_config.txt"),
        },
        runtime_client_factory=_dummy_pipe_factory,
    )

    assert service.config.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert service.config.max_new_tokens == 32
