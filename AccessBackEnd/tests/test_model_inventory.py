from pathlib import Path

from app.services.ai_pipeline.model_inventory import ModelInventoryConfig, ModelInventoryService


def _service(tmp_path: Path) -> ModelInventoryService:
    return ModelInventoryService(
        ModelInventoryConfig(
            provider="huggingface",
            model_name="",
            ollama_endpoint="",
            live_endpoint="",
            ollama_model_id="",
            huggingface_model_id="",
            huggingface_cache_dir=str(tmp_path),
            timeout_seconds=60,
        )
    )


def test_discover_local_huggingface_models_ignores_non_model_dirs(tmp_path):
    (tmp_path / "qwen2.5").mkdir()
    (tmp_path / "notes").mkdir()

    service = _service(tmp_path)
    assert service.discover_local_huggingface_models() == []


def test_discover_local_huggingface_models_accepts_cache_snapshot_dirs(tmp_path):
    model_dir = tmp_path / "models--Qwen--Qwen2.5-0.5B-Instruct"
    model_dir.mkdir()

    service = _service(tmp_path)
    discovered = service.discover_local_huggingface_models()

    assert [entry["id"] for entry in discovered] == ["models--Qwen--Qwen2.5-0.5B-Instruct"]


def test_discover_local_huggingface_models_accepts_materialized_dirs_with_markers(tmp_path):
    model_dir = tmp_path / "local-qwen"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")

    service = _service(tmp_path)
    discovered = service.discover_local_huggingface_models()

    assert [entry["id"] for entry in discovered] == ["local-qwen"]