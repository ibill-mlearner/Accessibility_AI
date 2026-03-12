from pathlib import Path

import pytest

from app.services.ai_pipeline_v2.factory import build_ai_service_from_config


class _DummyProvider:
    def invoke(self, prompt, context):
        return {"assistant_text": "ok"}

    def health(self):
        return {"ok": True}


def _dummy_provider_factory(**_kwargs):
    return _DummyProvider()


def _base_config(**overrides):
    config = {
        "AI_PROVIDER": "ollama",
        "AI_MODEL_NAME": "local-model",
        "AI_TIMEOUT_SECONDS": 60,
        "AI_OLLAMA_ENDPOINT": "http://localhost:11434/api/chat",
        "AI_OLLAMA_MODEL": "qwen2.5:0.5b",
        "AI_OLLAMA_OPTIONS": {},
        "AI_LIVE_ENDPOINT": "http://localhost:11434/api/chat",
        "AI_HUGGINGFACE_CACHE_DIR": None,
        "AI_HUGGINGFACE_ALLOW_DOWNLOAD": False,
    }
    config.update(overrides)
    return config


def test_build_ai_service_rejects_huggingface_local_only_without_local_model_dir(tmp_path: Path):
    config = _base_config(
        AI_PROVIDER="huggingface",
        AI_MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
        AI_HUGGINGFACE_CACHE_DIR=str(tmp_path),
        AI_HUGGINGFACE_ALLOW_DOWNLOAD=False,
    )

    with pytest.raises(ValueError, match="AI_PROVIDER=huggingface"):
        build_ai_service_from_config(config, provider_factory=_dummy_provider_factory)


def test_build_ai_service_accepts_huggingface_local_model_dir_when_download_disabled(tmp_path: Path):
    model_dir = tmp_path / "qwen-local"
    model_dir.mkdir()
    config = _base_config(
        AI_PROVIDER="huggingface",
        AI_MODEL_NAME=str(model_dir),
        AI_HUGGINGFACE_ALLOW_DOWNLOAD=False,
    )

    service = build_ai_service_from_config(config, provider_factory=_dummy_provider_factory)

    assert service is not None


def test_build_ai_service_accepts_huggingface_repo_id_when_download_enabled():
    config = _base_config(
        AI_PROVIDER="huggingface",
        AI_MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
        AI_HUGGINGFACE_ALLOW_DOWNLOAD=True,
    )

    service = build_ai_service_from_config(config, provider_factory=_dummy_provider_factory)

    assert service is not None
