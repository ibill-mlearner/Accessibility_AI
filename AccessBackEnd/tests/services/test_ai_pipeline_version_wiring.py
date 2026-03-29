from __future__ import annotations

import sys
import types

import pytest

from AccessBackEnd.app import create_app
from AccessBackEnd.app.services.ai_pipeline_gateway import AIPipelineGateway


def test_app_bootstrap_uses_ai_pipeline_thin_service(monkeypatch):
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    app = create_app("testing")

    service = app.extensions["ai_service"]
    wrapped = getattr(service, "_wrapped", service)
    assert wrapped.__class__.__module__ == "AccessBackEnd.app.services.ai_pipeline_gateway"


def test_gateway_run_interaction_surfaces_missing_ai_pipeline_runtime(monkeypatch):
    """Documents the current 500 root cause: missing ai_pipeline_thin runtime module."""
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setattr(
        AIPipelineGateway,
        "_load_ai_tool",
        staticmethod(lambda: (_ for _ in ()).throw(ModuleNotFoundError("No module named 'ai_pipeline_thin'"))),
    )

    app = create_app("testing")
    service = app.extensions["ai_service"]

    with app.app_context():
        with pytest.raises(ModuleNotFoundError, match="ai_pipeline_thin"):
            service.run_interaction("test", context={}, system_prompt="You are concise.")


def test_gateway_run_interaction_works_with_injected_local_runtime(monkeypatch):
    """Workaround spec: API path succeeds when ai_pipeline_thin runtime is available."""

    class _FakePipeline:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.model_loader = types.SimpleNamespace()

        def build_model(self):
            return object()

        def build_tokenizer(self):
            return object()

        def build_text(self, tokenizer):
            return "text"

        def build_model_inputs(self, tokenizer, text, model):
            return {"input_ids": [1]}

        def build_raw_generated_ids(self, model, model_inputs, max_new_tokens):
            return [[1, 2, 3]]

        def build_generated_ids(self, model_inputs, raw_generated_ids):
            return raw_generated_ids

        def build_response(self, tokenizer, generated_ids):
            return "ok"

    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin", types.ModuleType("ai_pipeline_thin"))
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin.ai_pipeline", types.SimpleNamespace(AIPipeline=_FakePipeline))

    app = create_app("testing")
    service = app.extensions["ai_service"]

    with app.app_context():
        payload = service.run_interaction("test", context={}, system_prompt="You are concise.")
    assert payload["assistant_text"] == "ok"
