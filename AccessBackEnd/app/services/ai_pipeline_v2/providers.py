from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .types import AIPipelineConfig, AIPipelineUpstreamError

logger = logging.getLogger(__name__)
_MAX_CONTEXT_MESSAGES = 4
def normalize_provider_name(provider: str | None) -> str:
    _ = provider
    return "local"


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


def normalize_backend_response(raw: Any) -> dict[str, Any]:
    parsed = _parse_maybe_json(raw)
    notes_raw = parsed.get("notes")
    notes = [str(item) for item in notes_raw] if isinstance(notes_raw, list) else ([notes_raw.strip()] if isinstance(notes_raw, str) and notes_raw.strip() else [])
    normalized: dict[str, Any] = {
        "assistant_text": str(parsed.get("assistant_text") or ""),
        "notes": notes,
        "meta": parsed.get("meta") if isinstance(parsed.get("meta"), dict) else {},
    }
    if isinstance(parsed.get("confidence"), (int, float)):
        normalized["confidence"] = float(parsed["confidence"])
    return normalized


def _parse_maybe_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        if any(key in raw for key in ("assistant_text", "result", "answer", "response_text", "response", "output", "text")):
            assistant_text = (
                raw.get("assistant_text")
                or raw.get("result")
                or raw.get("answer")
                or raw.get("response_text")
                or raw.get("response")
                or raw.get("output")
                or raw.get("text")
                or ""
            )
            return {**raw, "assistant_text": str(assistant_text)}
        message = raw.get("message") if isinstance(raw.get("message"), dict) else {}
        if message.get("content") is not None:
            return _parse_maybe_json(message.get("content"))
        return {"assistant_text": json.dumps(raw, ensure_ascii=False), "notes": ["non_json_fallback"]}

    text = str(raw or "").strip()
    for candidate in [text, *re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)]:
        try:
            obj = json.loads(candidate)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict):
            return _parse_maybe_json(obj)
    return {"assistant_text": text, "notes": ["non_json_fallback"]}


class BaseBackend:
    provider_name = "unknown"

    def __init__(self, *, config: AIPipelineConfig, model_id: str, endpoint: str = "") -> None:
        self.config = config
        self.model_id = model_id
        self.endpoint = endpoint

    def name(self) -> str:
        return self.provider_name

    def generate(self, prompt: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def invoke(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        request_id = request_id_from_context(context)
        try:
            payload = self.generate(prompt, str(context.get("system_instructions") or ""), context)
            normalized = normalize_backend_response(payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ai_provider.invoke.failed provider=%s request_id=%s", self.provider_name, request_id)
            raise map_exception(exc) from exc
        normalized.setdefault("meta", {}).update({"provider": self.provider_name, "model": self.model_id, "model_id": self.model_id})
        return normalized

    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.model_id), "model_id": self.model_id, "endpoint": self.endpoint}

    def inventory(self) -> list[dict[str, Any]]:
        return []



class OllamaBackend(BaseBackend):
    # Deprecated: kept as inert compatibility shim while Ollama is removed from MVP.
    provider_name = "ollama"

    def __init__(self, *, config: AIPipelineConfig, model_id: str, endpoint: str) -> None:
        super().__init__(config=config, model_id=model_id, endpoint=endpoint)

    def generate(self, prompt: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Ollama provider is deprecated for this project; use Hugging Face models only.")

    def inventory(self) -> list[dict[str, Any]]:
        return []

class HuggingFaceBackend(BaseBackend):
    provider_name = "huggingface"

    def __init__(self, *, config: AIPipelineConfig, model_id: str, endpoint: str = "") -> None:
        super().__init__(config=config, model_id=model_id, endpoint=endpoint)
        self._model: Any | None = None
        self._tokenizer: Any | None = None

    def _resolve_cache_dir(self, *, default_to_instance: bool = False) -> str | None:
        cache_dir = str(self.config.huggingface_cache_dir or "").strip()
        if cache_dir:
            return str(Path(cache_dir).expanduser())
        if default_to_instance:
            return str((Path(__file__).resolve().parents[3] / "instance" / "models").resolve())
        return None

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

    def _get_or_load_model_bundle(self) -> tuple[Any, Any]:
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer

        model_ref = self._resolve_model_reference()
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("transformers dependencies are required for HuggingFace provider") from exc

        cache_dir = self._resolve_cache_dir()
        self._model = AutoModelForCausalLM.from_pretrained(model_ref, cache_dir=cache_dir)
        self._tokenizer = AutoTokenizer.from_pretrained(model_ref, cache_dir=cache_dir)
        return self._model, self._tokenizer

    def generate(self, prompt: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        model, tokenizer = self._get_or_load_model_bundle()
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise assistant for accessibility learning support. "
                    "Return only JSON with assistant_text, confidence, and notes.\n"
                    f"System instructions: {clip(system_prompt, 400)}\n"
                    f"Context: {clip(json.dumps(sanitize_context(context), ensure_ascii=False), 500)}"
                ),
            },
            {"role": "user", "content": clip(prompt, 500)},
        ]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer(rendered, return_tensors="pt")
        model_inputs = {key: value.to(model.device) for key, value in model_inputs.items()}
        generated_tokens = model.generate(
            **model_inputs,
            max_new_tokens=self.config.max_new_tokens,
            temperature=self.config.temperature,
        )
        prompt_length = model_inputs["input_ids"].shape[-1]
        generated_only = generated_tokens[:, prompt_length:]
        assistant_text = tokenizer.batch_decode(generated_only, skip_special_tokens=True)[0].strip()
        return _parse_maybe_json(assistant_text)

    def health(self) -> dict[str, Any]:
        return {"ok": bool(self.model_id), "model_id": self.model_id, "status": "configured" if self.model_id else "not_configured"}

    def inventory(self) -> list[dict[str, Any]]:
        root = self._resolve_cache_dir(default_to_instance=True)
        if not root:
            return []
        root_path = Path(root).expanduser()
        if not root_path.exists() or not root_path.is_dir():
            return []
        models: list[dict[str, Any]] = []
        seen: set[str] = set()
        for child in root_path.iterdir():
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


# Backward-compatible aliases.
OllamaProvider = OllamaBackend
HuggingFaceProvider = HuggingFaceBackend
