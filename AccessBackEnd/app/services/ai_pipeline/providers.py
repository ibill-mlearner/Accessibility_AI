from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen
import requests

from .bootstrap import HuggingFaceModelBootstrap
from .types import PipelineRequest


_MAX_CONTEXT_MESSAGES = 4
_MAX_TEXT_CHARS = 500
_JSON_PRIORITY_KEYS = ("assistant_text", "result", "answer", "response_text")
# Keep the HuggingFace prompt template at module scope so invoke() stays focused on flow,
# and future prompt edits are easier to review without digging through method internals.
_HUGGINGFACE_PROMPT_TEMPLATE = """
You are a concise assistant for accessibility learning support.
{response_contract}
User prompt:
{prompt}
Context summary:
{context_summary}
""".strip()


def _clip_text(value: object, *, limit: int = _MAX_TEXT_CHARS) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}… [truncated]"


def _normalize_context_messages(messages: object) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        return []

    normalized_messages: list[dict[str, str]] = []
    for message in messages[-_MAX_CONTEXT_MESSAGES:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip().lower()
        content = _clip_text(message.get("content"), limit=300)
        if not role or not content:
            continue
        normalized_messages.append({"role": role, "content": content})

    return normalized_messages


def _sanitize_context(context: dict | None) -> dict:
    """Keep context compact and predictable for provider prompts."""
    if not isinstance(context, dict):
        return {}

    sanitized: dict[str, object] = {
        key: context[key]
        for key in ("chat_id", "class_id")
        if context.get(key) is not None
    }

    normalized_messages = _normalize_context_messages(context.get("messages"))
    if normalized_messages:
        sanitized["messages"] = normalized_messages

    return sanitized


def _json_response_contract() -> str:
    return (
        'Return only JSON with keys: '
        '{"assistant_text": string, "confidence": number|null, "notes": [string]}.'
    )



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

    def __init__(self, *, endpoint: str, model_name: str = "", timeout_seconds: int = 60) -> None:
        # Logic intent: configure endpoint and timeout once at startup.
        self.endpoint = endpoint
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def invoke(self, request: PipelineRequest) -> dict:
        # Logic intent:
        # 1) Send prompt/context as JSON.
        # 2) Parse JSON response and normalize metadata.
        if not self.endpoint:
            raise ValueError("HTTP endpoint must be configured")

        try:
            response = request.post(
                self.endpoint,
                json = {
                    "prompt": request.prompt,
                    "context": request.context,
                    "model": self.model_name
                },
                timeout = self.timeout_seconds
            ),
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to call AI endpoint: {exc}") from exc

        try:
            parsed = response.json()
        except ValueError as exc:
            raise RuntimeError("AI endpoint returned non-JSON response")

        if isinstance(parsed, dict):
            parsed.setdefault("meta", {})
            parsed["meta"]["provider"] = "http"
            parsed["meta"]["model"] = self.model_name
        return parsed


class OllamaProvider:
    """Provider for local/remote Ollama HTTP APIs."""

    def __init__(
        self,
        *,
        endpoint: str,
        model_id: str,
        options: dict | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        # Logic intent:
        # - Keep Ollama endpoint/model configuration explicit at service startup.
        self.endpoint = endpoint
        self.model_id = model_id
        self.options = options or {}
        self.timeout_seconds = timeout_seconds

    def invoke(self, request: PipelineRequest) -> dict:
        # Logic intent:
        # 1) Normalize endpoint to Ollama chat API (`/api/chat`).
        # 2) Send request payload with selected model + chat messages.
        # 3) Parse JSON robustly and normalize metadata.
        if not self.endpoint:
            raise ValueError("Ollama endpoint must be configured")
        if not self.model_id:
            raise ValueError("Ollama model_id must be configured")

        request_endpoint = self._resolve_chat_endpoint(self.endpoint)
        body_payload = {
            "model": self.model_id,
            "stream": False,
            "options": self.options,
            "messages": self._build_messages(request),
        }

        req = Request(
            request_endpoint,
            data=json.dumps(body_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                content = response.read().decode("utf-8")
        except URLError as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to call Ollama endpoint: {exc}") from exc

        parsed_payload = self._parse_ollama_payload(content)
        parsed_payload.setdefault("meta", {})
        parsed_payload["meta"].update(
            {
                "provider": "ollama",
                "model": self.model_id,
                "model_id": self.model_id,
                "endpoint": request_endpoint,
            }
        )
        return parsed_payload

    def _resolve_chat_endpoint(self, endpoint: str) -> str:
        """Resolve configured endpoint to Ollama's chat path.

        Accepts either a full `/api/chat` URL, a legacy `/api/generate` URL,
        or a base Ollama host URL.
        """

        cleaned = (endpoint or "").strip().rstrip("/")
        if not cleaned:
            return "/api/chat"

        lowered = cleaned.lower()
        if lowered.endswith("/api/chat"):
            return cleaned
        if lowered.endswith("/api/generate"):
            return f"{cleaned[:-len('/api/generate')]}/api/chat"

        if lowered.endswith("/api"):
            return f"{cleaned}/chat"

        return f"{cleaned}/api/chat"

    def _build_messages(self, request: PipelineRequest) -> list[dict[str, str]]:
        sanitized_context = _sanitize_context(request.context)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise assistant for accessibility learning support. "
                    f"{_json_response_contract()}"
                ),
            },
            {
                "role": "user",
                "content": _clip_text(request.prompt),
            },
        ]

        if sanitized_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Context summary: {json.dumps(sanitized_context, ensure_ascii=False)}",
                }
            )

        return messages

    def _parse_ollama_payload(self, content: str) -> dict:
        parsed = json.loads(content or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("Ollama response must be a JSON object")

        # Some Ollama deployments return already-structured JSON.
        if any(key in parsed for key in {"result", "answer", "confidence", "notes"}):
            return parsed

        # `/api/generate` returns `response`; `/api/chat` returns `message.content`.
        candidate_text = parsed.get("response")
        if not isinstance(candidate_text, str):
            message = parsed.get("message")
            if isinstance(message, dict):
                candidate_text = message.get("content")

        if not isinstance(candidate_text, str):
            return {"result": "", "raw": parsed}

        candidate_text = candidate_text.strip()
        try:
            candidate = json.loads(candidate_text)
            if isinstance(candidate, dict):
                return candidate
        except json.JSONDecodeError:
            pass

        start = candidate_text.find("{")
        end = candidate_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            clipped = candidate_text[start : end + 1]
            try:
                candidate = json.loads(clipped)
                if isinstance(candidate, dict):
                    return candidate
            except json.JSONDecodeError:
                pass

        return {"result": candidate_text, "raw": parsed}


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
        # Use the shared module-level template for readability and centralized prompt maintenance.

        prompt_template = PromptTemplate.from_template(_HUGGINGFACE_PROMPT_TEMPLATE)


        chain = prompt_template | llm | StrOutputParser()
        raw_text = chain.invoke(
            {
                "prompt": _clip_text(request.prompt),
                "context_summary": json.dumps(_sanitize_context(request.context), ensure_ascii=False),
                "response_contract": _json_response_contract(),
            }
        )
        provider_tag = "huggingface_langchain"
        try:
            parsed = self._parse_json(raw_text)
        except ValueError:
            parsed = {
                "assistant_text": "",
                "notes": ["non_json_fallback"],
                "meta": {
                    "provider": f"{provider_tag}:non_json_fallback",
                    "debug": {"raw_payload_preview": _clip_text(raw_text)},
                },
            }
        parsed.setdefault("meta", {})
        parsed["meta"].update(
            {
                "provider": parsed["meta"].get("provider", provider_tag),
                "model": self.model_id,
                "model_id": self.model_id,
            }
        )
        return parsed

    def _parse_json(self, raw_text: str) -> dict:
        # Logic intent:
        # - Robustly parse model output even when extra text appears around JSON.
        # - Fail loudly when model output is not JSON, keeping pipeline behavior explicit.
        normalized_text = (raw_text or "").strip()

        direct_parsed = self._parse_dict_or_none(normalized_text)
        if direct_parsed is not None:
            return direct_parsed

        candidates = self._extract_candidate_objects(normalized_text)
        selected_candidate = self._select_preferred_candidate(candidates)
        if selected_candidate is not None:
            return selected_candidate

        braced_candidate = self._parse_braced_json_candidate(normalized_text)
        if braced_candidate is not None:
            return braced_candidate

        raise ValueError("Model output is not valid JSON object")

    def _extract_candidate_objects(self, raw_text: str) -> list[dict]:
        candidates: list[dict] = []
        candidates.extend(self._extract_fenced_json_candidates(raw_text))
        candidates.extend(self._extract_raw_decode_candidates(raw_text))
        return candidates

    def _extract_fenced_json_candidates(self, raw_text: str) -> list[dict]:
        fenced_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
        candidates: list[dict] = []
        for block in fenced_pattern.findall(raw_text):
            parsed = self._parse_dict_or_none((block or "").strip())
            if parsed is not None:
                candidates.append(parsed)
        return candidates

    def _extract_raw_decode_candidates(self, raw_text: str) -> list[dict]:
        decoder = json.JSONDecoder()
        candidates: list[dict] = []
        idx = 0
        while idx < len(raw_text):
            try:
                parsed, end_idx = decoder.raw_decode(raw_text, idx)
            except json.JSONDecodeError:
                idx += 1
                continue

            if isinstance(parsed, dict):
                candidates.append(parsed)
            idx = max(end_idx, idx + 1)

        return candidates

    def _select_preferred_candidate(self, candidates: list[dict]) -> dict | None:
        for key in _JSON_PRIORITY_KEYS:
            for candidate in candidates:
                if key in candidate:
                    return candidate
        if candidates:
            return candidates[0]
        return None

    def _parse_braced_json_candidate(self, raw_text: str) -> dict | None:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return self._parse_dict_or_none(raw_text[start : end + 1])

    def _parse_dict_or_none(self, candidate: str) -> dict | None:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None
