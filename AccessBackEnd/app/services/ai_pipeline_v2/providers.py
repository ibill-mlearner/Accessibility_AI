from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import requests

from .types import AIPipelineConfig, AIPipelineUpstreamError

logger = logging.getLogger(__name__)
_MAX_CONTEXT_MESSAGES = 4
_PROVIDER_ALIASES: dict[str, set[str]] = {
    "ollama": {"ollama", "ollama_local"},
    "http": {"live", "live_agent", "http"},
    "huggingface": {"hf", "huggingface", "langchain_hf"},
}


def normalize_provider_name(provider: str | None) -> str:
    selected = str(provider or "").strip().lower()
    for canonical, aliases in _PROVIDER_ALIASES.items():
        if selected in aliases:
            return canonical
    return selected


def clip(value: Any, limit: int = 500) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else f"{text[:limit]}… [truncated]"


def sanitize_context(context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    data = {k: context[k] for k in ("chat_id", "class_id") if context.get(k) is not None}
    messages = [
        {"role": str(m.get("role") or "").lower(), "content": clip(m.get("content"), 300)}
        for m in context.get("messages", [])[-_MAX_CONTEXT_MESSAGES:]
        if isinstance(m, dict) and m.get("role") and m.get("content")
    ]
    if messages:
        data["messages"] = messages
    return data


def request_id_from_context(context: dict[str, Any] | None) -> str:
    if isinstance(context, dict) and context.get("request_id") is not None:
        return str(context.get("request_id"))
    return "n/a"


def map_exception(exc: Exception, *, source: str = "provider_runtime") -> AIPipelineUpstreamError:
    if isinstance(exc, AIPipelineUpstreamError):
        return exc
    return AIPipelineUpstreamError(str(exc) or "AI provider execution failed", details={"source": source, "exception": exc.__class__.__name__})


class BaseProvider:
    provider_name = "unknown"

    def __init__(self, *, config: AIPipelineConfig, model_id: str, endpoint: str = "") -> None:
        self.config = config
        self.model_id = model_id
        self.endpoint = endpoint

    def name(self) -> str:
        return self.provider_name

    def build_request(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"prompt": prompt, "context": context}

    def execute(self, payload: dict[str, Any]) -> Any:
        raise NotImplementedError

    def normalize_response(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            return self._parse_maybe_json(raw)
        raise TypeError("Pipeline provider must return a dictionary")

    def invoke(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        request_id = request_id_from_context(context)
        try:
            payload = self.build_request(prompt, context)
            raw = self.execute(payload)
            normalized = self.normalize_response(raw)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ai_provider.invoke.failed provider=%s request_id=%s", self.provider_name, request_id)
            raise map_exception(exc) from exc
        normalized.setdefault("meta", {}).update({"provider": self.provider_name, "model": self.model_id, "model_id": self.model_id})
        return normalized

    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.model_id), "model_id": self.model_id, "endpoint": self.endpoint}

    def inventory(self) -> list[dict[str, Any]]:
        return []

    @staticmethod
    def _parse_maybe_json(raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        for candidate in [text, *re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)]:
            try:
                obj = json.loads(candidate)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(obj, dict):
                return obj
        return {"assistant_text": text, "notes": ["non_json_fallback"]}


class HttpProvider(BaseProvider):
    provider_name = "http"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.endpoint:
            raise ValueError("HTTP endpoint must be configured")
        response = requests.post(self.endpoint, json={**payload, "model": self.model_id}, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()


class OllamaProvider(BaseProvider):
    provider_name = "ollama"

    def __init__(self, *, config: AIPipelineConfig, model_id: str, endpoint: str) -> None:
        super().__init__(config=config, model_id=model_id, endpoint=self._resolve_chat_endpoint(endpoint))

    def build_request(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": str(context.get("system_instructions") or "")},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
            "options": self.config.ollama_options or {},
        }

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        with urlopen(req, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8") or "{}")

    def normalize_response(self, raw: Any) -> dict[str, Any]:
        payload = super().normalize_response(raw)
        if any(key in payload for key in ("assistant_text", "result", "answer", "response_text", "confidence", "notes")):
            return payload
        text = payload.get("response") or ((payload.get("message") or {}).get("content") if isinstance(payload.get("message"), dict) else "")
        return self._parse_maybe_json(text if isinstance(text, str) else "")

    def inventory(self) -> list[dict[str, Any]]:
        tags_endpoint = self.endpoint.replace("/api/chat", "/api/tags")
        req = Request(tags_endpoint, headers={"Accept": "application/json"}, method="GET")
        with urlopen(req, timeout=self.config.timeout_seconds) as response:
            parsed = json.loads(response.read().decode("utf-8") or "{}")
        models = parsed.get("models") if isinstance(parsed, dict) else []
        if not isinstance(models, list):
            return []
        return [{"id": str(item.get("model") or item.get("name") or "").strip(), "source": "ollama", "path": None, "size": item.get("size"), "modified_at": item.get("modified_at")} for item in models if isinstance(item, dict) and (item.get("model") or item.get("name"))]

    @staticmethod
    def _resolve_chat_endpoint(endpoint: str) -> str:
        cleaned = (endpoint or "").strip().rstrip("/")
        if cleaned.lower().endswith("/api/chat"):
            return cleaned
        if cleaned.lower().endswith("/api/generate"):
            return f"{cleaned[:-len('/api/generate')]}/api/chat"
        if cleaned.lower().endswith("/api"):
            return f"{cleaned}/chat"
        return f"{cleaned}/api/chat"


class HuggingFaceProvider(BaseProvider):
    provider_name = "huggingface"

    def execute(self, payload: dict[str, Any]) -> str:
        model_ref = self._resolve_model_reference()
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("transformers dependencies are required for HuggingFace provider") from exc

        generator = hf_pipeline(
            "text-generation",
            model=AutoModelForCausalLM.from_pretrained(model_ref),
            tokenizer=AutoTokenizer.from_pretrained(model_ref),
            max_new_tokens=self.config.max_new_tokens,
            temperature=self.config.temperature,
        )
        rendered = (
            "You are a concise assistant for accessibility learning support. "
            "Return only JSON with assistant_text, confidence, and notes.\n"
            f"System instructions: {clip(payload['system_instructions'], 400)}\n"
            f"User prompt: {clip(payload['prompt'], 500)}\n"
            f"Context: {clip(payload['context_summary'], 500)}"
        )
        generated = generator(rendered)
        if isinstance(generated, list) and generated and isinstance(generated[0], dict):
            text = generated[0].get("generated_text")
            return str(text or "")
        return str(generated)

    def build_request(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "prompt": prompt,
            "context_summary": json.dumps(sanitize_context(context), ensure_ascii=False),
            "system_instructions": str(context.get("system_instructions") or ""),
        }

    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.model_id), "model_id": self.model_id, "status": "configured" if self.model_id else "not_configured"}

    def inventory(self) -> list[dict[str, Any]]:
        roots = [Path(self.config.huggingface_cache_dir).expanduser()] if self.config.huggingface_cache_dir else [Path(__file__).resolve().parents[3] / "instance" / "models"]
        models: list[dict[str, Any]] = []
        seen: set[str] = set()
        for root in roots:
            if not root.exists() or not root.is_dir():
                continue
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                marker = child / "config.json"
                if not (child.name.lower().startswith("models--") or marker.exists()):
                    continue
                resolved = child.resolve().as_posix()
                if resolved in seen:
                    continue
                seen.add(resolved)
                models.append({"id": child.name, "source": "huggingface_local", "path": resolved, "size": None, "modified_at": datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc).isoformat()})
        return sorted(models, key=lambda item: item["id"])

    def _resolve_model_reference(self) -> str:
        model_ref = str(self.model_id or "").strip()
        if not model_ref:
            raise ValueError("huggingface model_id must be configured")
        if self.config.huggingface_allow_download:
            return model_ref
        path = Path(model_ref).expanduser()
        if path.exists() and path.is_dir():
            return str(path)
        raise RuntimeError(
            "HuggingFace dynamic download is disabled in local-only mode for this POC. "
            "Provide a local model path in AI_MODEL_NAME or pre-download into AI_HUGGINGFACE_CACHE_DIR."
        )
