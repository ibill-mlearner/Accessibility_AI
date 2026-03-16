from pathlib import Path

import pytest

from AccessBackEnd.app.services.ai_pipeline_v2.config import AIPipelineV2ModuleConfig
from AccessBackEnd.app.services.ai_pipeline_v2.factory import build_ai_service_from_config


class _DummyProvider:
    def invoke(self, prompt, context):
        return {"assistant_text": "ok"}

    def health(self):
        return {"ok": True}


def _dummy_provider_factory(**_kwargs):
    return _DummyProvider()


def _base_module_config(**overrides):
    config = AIPipelineV2ModuleConfig(
        provider="ollama",
        model_name="local-model",
        timeout_seconds=60,
        ollama_endpoint="http://localhost:11434/api/chat",
        ollama_model_id="qwen2.5:0.5b",
        ollama_options={},
        live_endpoint="http://localhost:11434/api/chat",
        huggingface_cache_dir=None,
        huggingface_allow_download=False,
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_build_ai_service_rejects_huggingface_local_only_without_local_model_dir(tmp_path: Path):
    module_config = _base_module_config(
        provider="huggingface",
        model_name="Qwen/Qwen2.5-0.5B-Instruct",
        huggingface_cache_dir=str(tmp_path),
        huggingface_allow_download=False,
    )

    with pytest.raises(ValueError, match="AI_PROVIDER=huggingface"):
        build_ai_service_from_config(module_config, provider_factory=_dummy_provider_factory)


def test_build_ai_service_accepts_huggingface_local_model_dir_when_download_disabled(tmp_path: Path):
    model_dir = tmp_path / "qwen-local"
    model_dir.mkdir()
    module_config = _base_module_config(
        provider="huggingface",
        model_name=str(model_dir),
        huggingface_allow_download=False,
    )

    service = build_ai_service_from_config(module_config, provider_factory=_dummy_provider_factory)

    assert service is not None


def test_build_ai_service_accepts_mapping_fallback_for_transition():
    config = {
        "AI_PROVIDER": "huggingface",
        "AI_MODEL_NAME": "Qwen/Qwen2.5-0.5B-Instruct",
        "AI_HUGGINGFACE_ALLOW_DOWNLOAD": True,
    }

    service = build_ai_service_from_config(config=config, provider_factory=_dummy_provider_factory)

    assert service is not None


def test_build_ai_service_accepts_repo_id_with_writable_cache_dir(tmp_path: Path):
    cache_dir = tmp_path / "hf-cache"
    module_config = _base_module_config(
        provider="huggingface",
        model_name="Qwen/Qwen2.5-0.5B-Instruct",
        huggingface_cache_dir=str(cache_dir),
        huggingface_allow_download=True,
    )

    service = build_ai_service_from_config(module_config, provider_factory=_dummy_provider_factory)

    assert service is not None
    assert cache_dir.exists() and cache_dir.is_dir()


def test_build_ai_service_rejects_huggingface_cache_dir_when_path_is_file(tmp_path: Path):
    file_path = tmp_path / "hf-cache-file"
    file_path.write_text("x", encoding="utf-8")
    module_config = _base_module_config(
        provider="huggingface",
        model_name="Qwen/Qwen2.5-0.5B-Instruct",
        huggingface_cache_dir=str(file_path),
        huggingface_allow_download=True,
    )

    with pytest.raises(ValueError, match="AI_HUGGINGFACE_CACHE_DIR"):
        build_ai_service_from_config(module_config, provider_factory=_dummy_provider_factory)
