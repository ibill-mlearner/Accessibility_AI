from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from .exceptions import map_exception_to_upstream_error


@dataclass(slots=True)
class ModelInventoryConfig:
    provider: str
    model_name: str
    ollama_endpoint: str
    live_endpoint: str
    ollama_model_id: str
    huggingface_model_id: str
    huggingface_cache_dir: str | None
    timeout_seconds: int = 60


class ModelInventoryService:
    """Read-only discovery service for local AI model inventory."""

    def __init__(self, config: ModelInventoryConfig) -> None:
        self.config = config

    def list_available_models(self) -> dict[str, Any]:
        warnings: list[dict[str, Any]] = []
        ollama_models: list[dict[str, Any]] = []
        huggingface_models: list[dict[str, Any]] = []

        try:
            ollama_models = self.discover_ollama_models()
        except Exception as exc:  # noqa: BLE001
            mapped = map_exception_to_upstream_error(exc)
            warnings.append(
                {
                    "source": "ollama",
                    "message": str(mapped),
                    "details": mapped.details,
                }
            )

        try:
            huggingface_models = self.discover_local_huggingface_models()
        except Exception as exc:  # noqa: BLE001
            mapped = map_exception_to_upstream_error(exc)
            warnings.append(
                {
                    "source": "huggingface_local",
                    "message": str(mapped),
                    "details": mapped.details,
                }
            )

        return {
            "provider_defaults": {
                "provider": self.config.provider,
                "model_name": self.config.model_name,
                "ollama_model_id": self.config.ollama_model_id,
                "huggingface_model_id": self.config.huggingface_model_id,
            },
            "ollama": {
                "models": ollama_models,
                "count": len(ollama_models),
            },
            "huggingface_local": {
                "models": huggingface_models,
                "count": len(huggingface_models),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "meta": {
                "pipeline": "app.services.ai_pipeline",
                "warnings": warnings,
            },
        }

    @staticmethod
    def resolve_ollama_tags_endpoint(endpoint: str) -> str:
        cleaned = (endpoint or "").strip().rstrip("/")
        if not cleaned:
            return "http://127.0.0.1:11434/api/tags"

        lowered = cleaned.lower()
        if lowered.endswith("/api/chat"):
            return f"{cleaned[:-len('/api/chat')]}/api/tags"
        if lowered.endswith("/api/generate"):
            return f"{cleaned[:-len('/api/generate')]}/api/tags"
        if lowered.endswith("/api/tags"):
            return cleaned
        if lowered.endswith("/api"):
            return f"{cleaned}/tags"
        return f"{cleaned}/api/tags"

    def discover_ollama_models(self) -> list[dict[str, Any]]:
        endpoint = self.resolve_ollama_tags_endpoint(
            self.config.ollama_endpoint or self.config.live_endpoint
        )
        req = Request(endpoint, headers={"Accept": "application/json"}, method="GET")
        with urlopen(req, timeout=self.config.timeout_seconds) as response:
            content = response.read().decode("utf-8")

        parsed = json.loads(content or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("Ollama tags response must be a JSON object")

        models = parsed.get("models")
        if not isinstance(models, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("model") or item.get("name") or "").strip()
            if not model_id:
                continue
            normalized.append(
                {
                    "id": model_id,
                    "source": "ollama",
                    "path": None,
                    "size": item.get("size") if isinstance(item.get("size"), int) else None,
                    "modified_at": item.get("modified_at"),
                }
            )

        return normalized

    def discover_local_huggingface_models(self) -> list[dict[str, Any]]:
        search_roots = self.resolve_huggingface_model_roots()
        normalized: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        for root in search_roots:
            if not root.exists() or not root.is_dir():
                continue
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                resolved = child.resolve().as_posix()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                stat = child.stat()
                normalized.append(
                    {
                        "id": child.name,
                        "source": "huggingface_local",
                        "path": resolved,
                        "size": None,
                        "modified_at": datetime.fromtimestamp(
                            stat.st_mtime,
                            tz=timezone.utc,
                        ).isoformat(),
                    }
                )

        return sorted(normalized, key=lambda item: item["id"])

    def resolve_huggingface_model_roots(self) -> list[Path]:
        roots: list[Path] = []
        if self.config.huggingface_cache_dir:
            roots.append(Path(self.config.huggingface_cache_dir).expanduser())

        app_instance_models = Path(__file__).resolve().parents[3] / "instance" / "models"
        roots.append(app_instance_models)

        configured_model_path = Path(self.config.huggingface_model_id).expanduser()
        if configured_model_path.exists() and configured_model_path.is_dir():
            roots.append(configured_model_path.parent)

        unique_roots: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            resolved = root.resolve().as_posix()
            if resolved in seen:
                continue
            seen.add(resolved)
            unique_roots.append(root)
        return unique_roots