from __future__ import annotations

from AccessBackEnd.app import create_app


def test_module_configs_loaded_at_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_MODEL_NAME", "qwen2.5:0.5b")
    monkeypatch.setenv("AI_MAX_NEW_TOKENS", "45")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")

    app = create_app("testing")

    module_configs = app.extensions.get("module_configs")
    assert module_configs is not None
    assert "ai_pipeline_thin" in module_configs
    assert app.config["AI_PIPELINE_THIN_CONFIG"]["max_new_tokens"] == 45


def test_ai_service_uses_module_config_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")
    monkeypatch.setenv("AI_MAX_NEW_TOKENS", "111")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")

    app = create_app("testing")
    service = app.extensions["ai_service"]

    wrapped = getattr(service, "_wrapped", service)
    assert wrapped.provider_health()["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
