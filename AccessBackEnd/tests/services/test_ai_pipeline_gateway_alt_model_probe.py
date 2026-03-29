from __future__ import annotations

import sys
import types

from AccessBackEnd.app import create_app


def test_gateway_run_supports_alternate_qwen_model_name(monkeypatch):
    """Smoke spec: pipeline can be invoked with only a different model name."""

    selected_model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    observed = {"model_name": None}

    class _FakePipeline:
        def __init__(self, **kwargs):
            observed["model_name"] = kwargs.get("model_name_value")
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
            return "alt-model-ok"

    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin", types.ModuleType("ai_pipeline_thin"))
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin.ai_pipeline", types.SimpleNamespace(AIPipeline=_FakePipeline))

    app = create_app("testing")
    service = app.extensions["ai_service"]
    wrapped = getattr(service, "_wrapped", service)

    with app.app_context():
        result = wrapped.run(
            "Say hello.",
            model_name=selected_model_name,
            system_content="You are concise.",
        )

    assert result["assistant_text"] == "alt-model-ok"
    assert result["meta"]["model"] == selected_model_name
    assert observed["model_name"] == selected_model_name
