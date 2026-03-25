from __future__ import annotations

import sys
import types

import pytest

from AccessBackEnd.app.services.ai_pipeline_contracts import AIPipelineRequest, AIPipelineUpstreamError
from AccessBackEnd.app.services.ai_pipeline_thin_adapter import (
    AIPipelineService,
    PipelineContextRepository,
    PipelineInteractionRunner,
)


class _FakePipeline:
    last_instance = None

    def __init__(self, **kwargs):
        type(self).last_instance = self
        self.kwargs = kwargs
        self.model_loader = types.SimpleNamespace()

    def build_model(self):
        return object()

    def build_tokenizer(self):
        return object()

    def build_text(self, tokenizer):
        return "prompt"

    def build_model_inputs(self, tokenizer, text, model):
        return {"input_ids": [1]}

    def build_raw_generated_ids(self, model, model_inputs, max_new_tokens):
        return [[1, 2, 3]]

    def build_generated_ids(self, model_inputs, raw_generated_ids):
        return raw_generated_ids

    def build_response(self, tokenizer, generated_ids):
        return "ok"


class _FakePipelineWithDType(_FakePipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_loader = types.SimpleNamespace(dtype=None)


def test_runner_uses_dtype_when_supported(monkeypatch):
    module = types.SimpleNamespace(AIPipeline=_FakePipelineWithDType)
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin", types.ModuleType("ai_pipeline_thin"))
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin.ai_pipeline", module)

    runner = PipelineInteractionRunner(model_name="repo/model", download_locally=True)
    response = runner.run(prompt="Hello", system_content="Be concise")

    assert response == "ok"
    assert module.AIPipeline.last_instance.model_loader.dtype == "auto"
    assert not hasattr(module.AIPipeline.last_instance.model_loader, "torch_dtype")


def test_runner_falls_back_to_torch_dtype_for_legacy_loader(monkeypatch):
    module = types.SimpleNamespace(AIPipeline=_FakePipeline)
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin", types.ModuleType("ai_pipeline_thin"))
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin.ai_pipeline", module)

    runner = PipelineInteractionRunner(model_name="repo/model", download_locally=True)
    response = runner.run(prompt="Hello", system_content="Be concise")

    assert response == "ok"
    assert module.AIPipeline.last_instance.model_loader.torch_dtype == "auto"


def test_runner_wraps_runtime_errors_as_upstream_error(monkeypatch):
    class _FailingPipeline(_FakePipeline):
        def build_model(self):
            raise RuntimeError("boom")

    module = types.SimpleNamespace(AIPipeline=_FailingPipeline)
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin", types.ModuleType("ai_pipeline_thin"))
    monkeypatch.setitem(sys.modules, "ai_pipeline_thin.ai_pipeline", module)

    runner = PipelineInteractionRunner(model_name="repo/model", download_locally=True)
    with pytest.raises(AIPipelineUpstreamError, match="Model invocation failed"):
        runner.run(prompt="Hello", system_content="Be concise")


def test_service_uses_configured_model_runner(monkeypatch):
    class _CaptureRunner:
        def __init__(self, model_name):
            self.model_name = model_name
            self.download_locally = True
            self.max_new_tokens = 32
            self.calls = []

        def run(self, *, prompt: str, system_content: str) -> str:
            self.calls.append((prompt, system_content, self.model_name))
            return f"ok:{self.model_name}"

    def _fake_run(self, *, prompt: str, system_content: str) -> str:
        return f"ok:{self.model_name}"

    monkeypatch.setattr(PipelineInteractionRunner, "run", _fake_run)

    default_runner = _CaptureRunner("default/model")
    service = AIPipelineService(
        model_name="default/model",
        context_repo=PipelineContextRepository(config_system_content="guardrail"),
        interaction_runner=default_runner,
    )

    result = service.run(AIPipelineRequest(prompt="hello"))

    assert result["assistant_text"] == "ok:default/model"
    assert result["meta"]["selected_model_id"] == "default/model"
