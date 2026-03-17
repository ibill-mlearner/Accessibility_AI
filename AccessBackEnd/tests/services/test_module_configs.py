from __future__ import annotations

from pathlib import Path

from AccessBackEnd.app.auth.config import AuthModuleConfig
from AccessBackEnd.app.services.ai_pipeline_v2.config import AIPipelineV2ModuleConfig
from AccessBackEnd.app.services.logging.module_config import LoggingModuleConfig


def test_ai_pipeline_module_config_defaults(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    cfg = AIPipelineV2ModuleConfig.from_env()
    assert cfg.provider == "huggingface"
    assert cfg.timeout_seconds == 60


def test_ai_pipeline_module_config_preserves_supplied_values(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "HuggingFace ")
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "0")
    cfg = AIPipelineV2ModuleConfig.from_env()

    assert cfg.provider == "huggingface"
    assert cfg.timeout_seconds == 0


def test_ai_pipeline_module_config_normalizes_relative_model_dir(monkeypatch):
    monkeypatch.setenv("AI_MODEL_NAME", "instance/models/Qwen2.5-0.5B-Instruct")
    cfg = AIPipelineV2ModuleConfig.from_env()

    expected = (Path(__file__).resolve().parents[2] / "instance" / "models" / "Qwen2.5-0.5B-Instruct").resolve()
    assert Path(cfg.model_name).resolve() == expected


def test_ai_pipeline_module_config_default_model_dir_uses_backend_instance(monkeypatch):
    monkeypatch.delenv("AI_MODEL_NAME", raising=False)
    cfg = AIPipelineV2ModuleConfig.from_env()

    expected = (Path(__file__).resolve().parents[2] / "instance" / "models" / "Qwen2.5-0.5B-Instruct").resolve()
    assert Path(cfg.model_name).resolve() == expected


def test_auth_module_config_defaults(monkeypatch):
    monkeypatch.delenv("AUTH_PROVIDER", raising=False)
    cfg = AuthModuleConfig.from_env()
    assert cfg.provider == "local"
    assert cfg.jwt_access_expires.total_seconds() == 1800


def test_logging_module_config_preserves_supplied_values(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", " debug ")
    cfg = LoggingModuleConfig.from_env()

    assert cfg.level == " debug "
