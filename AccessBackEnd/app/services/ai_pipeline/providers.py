from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from .bootstrap import HuggingFaceModelBootstrap
from .types import PipelineRequest


class AIProvider(Protocol):
    """Provider contract for pipeline execution.

    # Logic intent:
    # - Make each provider interchangeable under a common `invoke` API.
    # - Keep the pipeline independent from specific vendor SDKs.
    """

    def invoke(self, request: PipelineRequest) -> dict:
        # Logic intent: execute prompt and return JSON-compatible dictionary.
        ...


class MockJSONProvider:
    """Deterministic provider using a local JSON fixture."""

    def __init__(self, *, mock_resource_path: str) -> None:
        # Logic intent: keep mock mode simple and dependency-free.
        self.mock_resource_path = mock_resource_path

    def invoke(self, request: PipelineRequest) -> dict:
        # Logic intent:
        # 1) Load fixture from disk.
        # 2) Return fixture with metadata useful for debugging and tests.
        resource = Path(self.mock_resource_path)
        if not resource.exists():
            raise FileNotFoundError(f"Mock AI resource not found: {resource}")

        payload = json.loads(resource.read_text(encoding="utf-8"))
        payload.setdefault("meta", {})
        payload["meta"].update({"provider": "mock_json", "prompt_echo": request.prompt})
        return payload


class HTTPEndpointProvider:
    """Provider for JSON-over-HTTP AI services."""

    def __init__(self, *, endpoint: str, timeout_seconds: int = 60) -> None:
        # Logic intent: configure endpoint and timeout once at startup.
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def invoke(self, request: PipelineRequest) -> dict:
        # Logic intent:
        # 1) Send prompt/context as JSON.
        # 2) Parse JSON response and normalize metadata.
        if not self.endpoint:
            raise ValueError("HTTP endpoint must be configured")

        body = json.dumps({"prompt": request.prompt, "context": request.context}).encode("utf-8")
        req = Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                content = response.read().decode("utf-8")
        except URLError as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to call AI endpoint: {exc}") from exc

        parsed = json.loads(content or "{}")
        if isinstance(parsed, dict):
            parsed.setdefault("meta", {})
            parsed["meta"]["provider"] = "http"
        return parsed


class HuggingFaceLangChainProvider:
    """Local HuggingFace model provider using LangChain wrappers.

    # Logic intent:
    # - Download/cache a model from HuggingFace Hub if not present.
    # - Drive text generation through LangChain-compatible interfaces.
    # - Force JSON-only responses and parse them into dictionaries.
    """

    def __init__(
        self,
        *,
        model_id: str,
        cache_dir: str | None = None,
        max_new_tokens: int = 256,
        temperature: float = 0.1,
    ) -> None:
        # Logic intent: capture all model/runtime knobs in provider config.
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._bootstrap = HuggingFaceModelBootstrap(model_id=model_id, cache_dir=cache_dir)

    def invoke(self, request: PipelineRequest) -> dict:
        # Logic intent:
        # 1) Ensure local model artifacts exist.
        # 2) Build a strict JSON instruction prompt.
        # 3) Execute via transformers + LangChain and parse output into dict.
        model_path = self._bootstrap.ensure_model()

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline
            from langchain_community.llms import HuggingFacePipeline
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import StrOutputParser
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "LangChain + transformers dependencies are required for HuggingFace provider."
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path)
        generator = hf_pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
        )

        llm = HuggingFacePipeline(pipeline=generator)
        prompt_template = PromptTemplate.from_template(
            """
You are a JSON API assistant. Return only valid JSON object without markdown.
User prompt: {prompt}
Context JSON: {context_json}
Required response schema: {{"result": string, "confidence": number, "notes": [string]}}
""".strip()
        )
        chain = prompt_template | llm | StrOutputParser()
        raw_text = chain.invoke({"prompt": request.prompt, "context_json": json.dumps(request.context)})
        parsed = self._parse_json(raw_text)
        parsed.setdefault("meta", {})
        parsed["meta"].update({"provider": "huggingface_langchain", "model_id": self.model_id})
        return parsed

    def _parse_json(self, raw_text: str) -> dict:
        # Logic intent:
        # - Robustly parse model output even when extra text appears around JSON.
        # - Fail loudly when model output is not JSON, keeping pipeline behavior explicit.
        raw_text = (raw_text or "").strip()
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw_text[start : end + 1]
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("Model output is not valid JSON object")
