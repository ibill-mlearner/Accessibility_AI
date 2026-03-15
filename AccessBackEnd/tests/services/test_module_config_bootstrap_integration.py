from __future__ import annotations

from AccessBackEnd.app import create_app


def test_module_configs_loaded_at_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL_NAME", "qwen2.5:0.5b")
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")

    app = create_app("testing")

    module_configs = app.extensions.get("module_configs")
    assert module_configs is not None
    assert "ai_pipeline_v2" in module_configs
    assert app.config["AI_PIPELINE_V2_CONFIG"].timeout_seconds == 45


def test_ai_service_uses_module_config_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_PROVIDER", "huggingface")
    monkeypatch.setenv("AI_MODEL_NAME", tmp_path.as_posix())
    monkeypatch.setenv("AI_HUGGINGFACE_ALLOW_DOWNLOAD", "false")
    monkeypatch.setenv("AI_ENABLE_OLLAMA_FALLBACK", "true")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")

    app = create_app("testing")
    service = app.extensions["ai_service"]

    wrapped = getattr(service, "_wrapped", service)
    assert wrapped.config.provider == "huggingface"
    assert wrapped.config.enable_ollama_fallback_on_hf_local_only_error is True
