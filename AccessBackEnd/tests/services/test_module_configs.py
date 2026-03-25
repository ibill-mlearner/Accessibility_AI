from __future__ import annotations

from AccessBackEnd.app.auth.config import AuthModuleConfig
from AccessBackEnd.app.extensions import _build_ai_pipeline_thin_config
from AccessBackEnd.app.services.logging.module_config import LoggingModuleConfig


def test_ai_pipeline_module_config_defaults(monkeypatch):
    monkeypatch.delenv("AI_MODEL_NAME", raising=False)
    monkeypatch.delenv("AI_MAX_NEW_TOKENS", raising=False)
    cfg = _build_ai_pipeline_thin_config()
    assert cfg["model_name"] == "HuggingFaceTB/SmolLM2-360M-Instruct"
    assert cfg["max_new_tokens"] == 256


def test_ai_pipeline_module_config_preserves_supplied_values(monkeypatch):
    monkeypatch.setenv("AI_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct ")
    monkeypatch.setenv("AI_MAX_NEW_TOKENS", "111")
    cfg = _build_ai_pipeline_thin_config()

    assert cfg["model_name"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert cfg["max_new_tokens"] == 111


def test_auth_module_config_defaults(monkeypatch):
    monkeypatch.delenv("AUTH_PROVIDER", raising=False)
    cfg = AuthModuleConfig.from_env()
    assert cfg.provider == "local"
    assert cfg.jwt_access_expires.total_seconds() == 1800


def test_logging_module_config_preserves_supplied_values(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", " debug ")
    cfg = LoggingModuleConfig.from_env()

    assert cfg.level == " debug "
