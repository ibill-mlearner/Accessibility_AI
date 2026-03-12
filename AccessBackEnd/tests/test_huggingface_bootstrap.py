from pathlib import Path

import pytest
from app.services.ai_pipeline.bootstrap import HuggingFaceModelBootstrap


def test_ensure_model_uses_local_path_when_present(tmp_path: Path):
    model_dir = tmp_path / "my-model"
    model_dir.mkdir()

    bootstrap = HuggingFaceModelBootstrap(model_id=str(model_dir), allow_download=False)

    assert bootstrap.ensure_model() == model_dir


def test_ensure_model_uses_cached_snapshot_when_available(tmp_path: Path):
    snapshot_dir = tmp_path / "models--Qwen--Qwen2.5-0.5B-Instruct" / "snapshots" / "abc123"
    snapshot_dir.mkdir(parents=True)

    bootstrap = HuggingFaceModelBootstrap(
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        cache_dir=str(tmp_path),
        allow_download=False,
    )

    assert bootstrap.ensure_model() == snapshot_dir


def test_ensure_model_raises_in_local_only_mode_without_local_artifacts(tmp_path: Path):
    bootstrap = HuggingFaceModelBootstrap(
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        cache_dir=str(tmp_path),
        allow_download=False,
    )

    with pytest.raises(RuntimeError, match="dynamic download is disabled"):
        bootstrap.ensure_model()


def test_ensure_model_uses_cache_alias_directory_when_available(tmp_path: Path):
    alias_dir = tmp_path / "llama3.2"
    alias_dir.mkdir(parents=True)

    bootstrap = HuggingFaceModelBootstrap(
        model_id="llama3.2",
        cache_dir=str(tmp_path),
        allow_download=False,
    )

    assert bootstrap.ensure_model() == alias_dir