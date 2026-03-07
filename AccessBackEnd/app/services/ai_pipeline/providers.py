from __future__ import annotations

import json, logging, re, requests
from pathlib import Path
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from .bootstrap import HuggingFaceModelBootstrap

_MAX_CONTEXT_MESSAGES = 4
logger = logging.getLogger(__name__)
_PROVIDER_ALIASES: dict[str, set[str]] = {
    "mock_json": {"mock", "mock_json", "json"},
    "ollama": {"ollama", "ollama_local"},
    "http": {"live", "live_agent", "http"},
    "huggingface": {"hf", "huggingface", "langchain_hf"},
}

def _clip(
    value: Any, 
    limit: int = 500
) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else f"{text[:limit]}… [truncated]"

def normalize_provider_name(provider: str | None) -> str:
    selected = str(provider or "").strip().lower()
    for canonical, aliases in _PROVIDER_ALIASES.items():
        if selected in aliases:
            return canonical
    return selected
def _sanitize_context(context: dict[str, Any] | None) -> dict[str, Any]:

    if not isinstance(context, dict):
        return {}

    data = {k: context[k] for k in ("chat_id", "class_id") if context.get(k) is not None}
    messages = [
        {"role": str(m.get("role") or "").lower(), "content": _clip(m.get("content"), 300)}
        for m in context.get("messages", [])[-_MAX_CONTEXT_MESSAGES:]
        if isinstance(m, dict) and m.get("role") and m.get("content")
    ]
    if messages:
        data["messages"] = messages
    return data

def _contract() -> str:
    return 'Return only JSON: {"assistant_text": string, "confidence": number|null, "notes": [string]}.'


def _request_id_from_context(context: dict[str, Any] | None) -> str:
    if isinstance(context, dict) and context.get("request_id") is not None:
        return str(context.get("request_id"))
    return "n/a"

def _context_messages_count(context: dict[str, Any] | None) -> int:
    if not isinstance(context, dict):
        return 0
    messages = context.get("messages")
    return len(messages) if isinstance(messages, list) else 0

class AIProvider(Protocol):
    def invoke(
        self, 
        prompt: str, 
        context: dict[str, Any]
    ) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...
    def name(self) -> str: ...
    def capabilities(self) -> dict[str, Any]: ...


class MockJSONProvider:
    def __init__(
        self, *, 
        mock_resource_path: str
    ) -> None:
        self.mock_resource_path = mock_resource_path

    def invoke(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        request_id = _request_id_from_context(context)
        logger.debug(
            "ai_provider.invoke.start request_id=%s provider=mock_json prompt_len=%s context_messages_count=%s prompt_preview=%r",
            request_id,
            len(prompt or ""),
            _context_messages_count(context),
            _clip(prompt, 200),
        )
        resource = Path(self.mock_resource_path)
        if not resource.exists():
            raise FileNotFoundError(f"Mock AI resource not found: {resource}")
        payload = json.loads(resource.read_text(encoding="utf-8"))
        payload.setdefault("meta", {}).update({"provider": "mock_json", "prompt_echo": prompt})
        logger.debug(
            "ai_provider.invoke.end request_id=%s provider=mock_json response_keys_count=%s response_preview=%r",
            request_id,
            len(payload.keys()) if isinstance(payload, dict) else 0,
            _clip(payload, 200),
        )
        return payload

    def health(self) -> dict[str, Any]: 
        return {"ok": Path(self.mock_resource_path).exists()}

    def name(self) -> str: 
        return "mock_json"

    def capabilities(self) -> dict[str, Any]: 
        return {"mode": "static_json"}

class HTTPEndpointProvider:
    def __init__(
        self, *, 
        endpoint: str, 
        model_name: str = "", 
        timeout_seconds: int = 60
    ) -> None:
        self.endpoint = endpoint
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def invoke(
        self, 
        prompt: str, 
        context: dict[str, Any]
    ) -> dict[str, Any]:

        if not self.endpoint:
            raise ValueError("HTTP endpoint must be configured")

        request_id = _request_id_from_context(context)
        logger.debug(

            "ai_provider.invoke.start request_id=%s provider=http endpoint=%s model=%s timeout_seconds=%s prompt_len=%s context_messages_count=%s prompt_preview=%r",
            request_id,
            self.endpoint,
            self.model_name,
            self.timeout_seconds,
            len(prompt or ""),
            _context_messages_count(context),
            _clip(prompt, 200)
        )

        try:
            response = requests.post(
                self.endpoint,
                json={"prompt": prompt, "context": context, "model": self.model_name},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to call AI endpoint: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("AI endpoint returned non-JSON response") from exc
        if isinstance(payload, dict):
            payload.setdefault("meta", {}).update({"provider": "http", "model": self.model_name})

        logger.debug(
            "ai_provider.invoke.end request_id=%s provider=http endpoint=%s model=%s response_keys_count=%s response_preview=%r",
            request_id,
            self.endpoint,
            self.model_name,
            len(payload.keys()) if isinstance(payload, dict) else 0,
            _clip(payload, 200)
        )
        return payload

    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.endpoint), "endpoint": self.endpoint}

    def name(self) -> str:
        return "http"

    def capabilities(self) -> dict[str, Any]:
        return {"transport": "http_json"}


class OllamaProvider:
    def __init__(
        self, 
        *, 
        endpoint: str, 
        model_id: str, 
        options: dict | None = None, 
        timeout_seconds: int = 60
    ) -> None:

        self.endpoint = endpoint
        self.model_id = model_id
        self.options = options or {}
        self.timeout_seconds = timeout_seconds

    def invoke(
        self, 
        prompt: str, 
        context: dict[str, Any]
    ) -> dict[str, Any]:

        if not self.endpoint or not self.model_id:
            raise ValueError("Ollama endpoint and model_id must be configured")
        endpoint = self._resolve_chat_endpoint(self.endpoint)
        request_id = _request_id_from_context(context)
        logger.debug(
            "ai_provider.invoke.start request_id=%s provider=ollama endpoint=%s model=%s timeout_seconds=%s prompt_len=%s context_messages_count=%s prompt_preview=%r",
            request_id,
            endpoint,
            self.model_id,
            self.timeout_seconds,
            len(prompt or ""),
            _context_messages_count(context),
            _clip(prompt, 200)
        )

        body = {
            "model": self.model_id,
            "stream": False,
            "options": self.options,
            "messages": [
                {"role": "system", "content": f"You are a concise assistant for accessibility learning support. {_contract()}"},
                *([{"role": "system", "content": _clip(context.get("system_instructions"))}] if context.get("system_instructions") else []),
                {"role": "user", "content": _clip(prompt)},
                *([{"role": "system", "content": f"Context summary: {json.dumps(_sanitize_context(context), ensure_ascii=False)}"}] if _sanitize_context(context) else []),
            ],
        }

        req = Request(endpoint, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except URLError as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to call Ollama endpoint: {exc}") from exc
        payload = self._parse_payload(raw)
        payload.setdefault("meta", {}).update({"provider": "ollama", "model": self.model_id, "model_id": self.model_id, "endpoint": endpoint})
        
        logger.debug(
            "ai_provider.invoke.end request_id=%s provider=ollama endpoint=%s model=%s response_keys_count=%s response_preview=%r",
            request_id,
            endpoint,
            self.model_id,
            len(payload.keys()) if isinstance(payload, dict) else 0,
            _clip(payload, 200)
        )
        return payload

    @staticmethod
    def _resolve_chat_endpoint(
            endpoint: str
        ) -> str:

        cleaned = (endpoint or "").strip().rstrip("/")
        if cleaned.lower().endswith("/api/chat"):
            return cleaned
        if cleaned.lower().endswith("/api/generate"):
            return f"{cleaned[:-len('/api/generate')]}/api/chat"
        if cleaned.lower().endswith("/api"):
            return f"{cleaned}/chat"
        return f"{cleaned}/api/chat"

    @staticmethod
    def _parse_payload(raw: str) -> dict[str, Any]:

        parsed = json.loads(raw or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("Ollama response must be a JSON object")
        if any(k in parsed for k in ("assistant_text", "result", "answer", "response_text", "confidence", "notes")):
            return parsed
        text = parsed.get("response") or ((parsed.get("message") or {}).get("content") if isinstance(parsed.get("message"), dict) else "")
        if not isinstance(text, str):
            return {"result": "", "raw": parsed}
        text = text.strip()
        for candidate in (text, text[text.find("{"): text.rfind("}") + 1] if "{" in text and "}" in text else ""):
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:  # noqa: BLE001
                pass
        return {"result": text, "raw": parsed}
    
    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.endpoint and self.model_id), "endpoint": self.endpoint, "model_id": self.model_id}

    def name(self) -> str:
        return "ollama"

    def capabilities(self) -> dict[str, Any]:
        return {"stream": False, "contract": "json"}


class HuggingFaceLangChainProvider:
    def __init__(
        self, 
        *, 
        model_id: str, 
        cache_dir: str | None = None, 
        max_new_tokens: int = 256, 
        temperature: float = 0.1
    ) -> None:

        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._bootstrap = HuggingFaceModelBootstrap(model_id=model_id, cache_dir=cache_dir)

    def invoke(
        self, 
        prompt: str, 
        context: dict[str, Any]
    ) -> dict[str, Any]:

        request_id = _request_id_from_context(context)
        logger.debug(
            "ai_provider.invoke.start request_id=%s provider=huggingface_langchain model=%s timeout_seconds=n/a prompt_len=%s context_messages_count=%s prompt_preview=%r",
            request_id,
            self.model_id,
            len(prompt or ""),
            _context_messages_count(context),
            _clip(prompt, 200)
        )
        model_path = self._bootstrap.ensure_model()
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline
            from langchain_community.llms import HuggingFacePipeline
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import PromptTemplate
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("LangChain + transformers dependencies are required for HuggingFace provider.") from exc
        generator = hf_pipeline(
            "text-generation", 
            model=AutoModelForCausalLM.from_pretrained(model_path), 
            tokenizer=AutoTokenizer.from_pretrained(model_path), 
            max_new_tokens=self.max_new_tokens, 
            temperature=self.temperature
        )
        
        chain = PromptTemplate.from_template(
            "You are a concise assistant for accessibility learning support.\n{contract}\nUser prompt:\n{prompt}\nContext summary:\n{context}"
        ) | HuggingFacePipeline(pipeline=generator) | StrOutputParser()

        raw = chain.invoke(
            {
                "prompt": _clip(prompt), 
                "context": json.dumps(_sanitize_context(context), 
                ensure_ascii=False), 
                "contract": _contract()
            }
        )
        parsed = self._parse_json(raw)
        parsed.setdefault("meta", {}).update(
            {
                "provider": parsed.get("meta", {}).get("provider", "huggingface_langchain"), 
                "model": self.model_id, 
                "model_id": self.model_id
            }
        )
        logger.debug(
            "ai_provider.invoke.end request_id=%s provider=huggingface_langchain model=%s response_keys_count=%s response_preview=%r",
            request_id,
            self.model_id,
            len(parsed.keys()) if isinstance(parsed, dict) else 0,
            _clip(parsed, 200),
        )
        return parsed

    def _parse_json(self, raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        for candidate in [text, *re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)]:
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:  # noqa: BLE001
                continue
        decoder = json.JSONDecoder()
        i = 0
        while i < len(text):
            try:
                obj, end = decoder.raw_decode(text, i)
                if isinstance(obj, dict):
                    return obj
                i = max(end, i + 1)
            except json.JSONDecodeError:
                i += 1
        if "{" in text and "}" in text:
            try:
                obj = json.loads(text[text.find("{"): text.rfind("}") + 1])
                if isinstance(obj, dict):
                    return obj
            except Exception:  # noqa: BLE001
                pass
        return {"assistant_text": "", "notes": ["non_json_fallback"], "meta": {"provider": "huggingface_langchain:non_json_fallback", "debug": {"raw_payload_preview": _clip(text)}}}

    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.model_id), "model_id": self.model_id}

    def name(self) -> str:
        return "huggingface_langchain"

    def capabilities(self) -> dict[str, Any]:
        return {"runtime": "langchain_transformers"}

def create_provider(
    *, 
    provider: str, 
    model_name: str = "", 
    mock_resource_path: str = "", 
    live_endpoint: str = "", 
    ollama_endpoint: str = "", 
    ollama_model_id: str = "", 
    ollama_options: dict[str, Any] | None = None, 
    timeout_seconds: int = 60, 
    huggingface_model_id: str = "", 
    huggingface_cache_dir: str | None = None, 
    max_new_tokens: int = 256, 
    temperature: float = 0.1
) -> AIProvider:
    selected = normalize_provider_name(provider or "ollama")
    logger.debug(
        "ai_provider.select provider=%s live_endpoint=%s ollama_endpoint=%s model_name=%s ollama_model_id=%s timeout_seconds=%s",
        selected,
        live_endpoint,
        ollama_endpoint,
        model_name,
        ollama_model_id,
        timeout_seconds
    )
    if selected == "mock_json":
        return MockJSONProvider(mock_resource_path=mock_resource_path)
    if selected == "ollama":
        return OllamaProvider(endpoint=ollama_endpoint or live_endpoint, model_id=ollama_model_id or model_name or huggingface_model_id, options=ollama_options, timeout_seconds=timeout_seconds)
    if selected == "http":
        return HTTPEndpointProvider(endpoint=live_endpoint, model_name=model_name, timeout_seconds=timeout_seconds)
    if selected == "huggingface":
        return HuggingFaceLangChainProvider(model_id=huggingface_model_id, cache_dir=huggingface_cache_dir, max_new_tokens=max_new_tokens, temperature=temperature)
    raise ValueError(f"Unsupported AI provider: {provider}")