from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_WEIGHT_CANDIDATES = (
    "pytorch_model.bin",
    "model.safetensors",
    "pytorch_model.bin.index.json",
    "model.safetensors.index.json",
)
_TOKENIZER_CANDIDATES = ("tokenizer.json", "tokenizer_config.json")


def model_artifact_diagnostics(path: Path) -> dict[str, Any]:
    config_file = path / "config.json"
    diagnostics: dict[str, Any] = {
        "resolved_model_dir": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "config_json_exists": config_file.exists(),
        "config_json_parseable": False,
        "config_model_type_present": False,
        "tokenizer_files_present": False,
        "tokenizer_files_found": [],
        "weight_files_present": False,
        "weight_files_found": [],
        "directory_listing": [],
    }

    if path.exists() and path.is_dir():
        diagnostics["directory_listing"] = sorted(child.name for child in path.iterdir())[:20]

    if config_file.exists() and config_file.is_file():
        try:
            config_payload = json.loads(config_file.read_text(encoding="utf-8"))
            diagnostics["config_json_parseable"] = isinstance(config_payload, dict)
            diagnostics["config_model_type_present"] = isinstance(config_payload, dict) and bool(config_payload.get("model_type"))
        except Exception:  # noqa: BLE001
            diagnostics["config_json_parseable"] = False

    found_tokenizers = [name for name in _TOKENIZER_CANDIDATES if (path / name).exists()]
    diagnostics["tokenizer_files_found"] = found_tokenizers
    diagnostics["tokenizer_files_present"] = bool(found_tokenizers)

    found_weights = [name for name in _WEIGHT_CANDIDATES if (path / name).exists()]
    diagnostics["weight_files_found"] = found_weights
    diagnostics["weight_files_present"] = bool(found_weights)
    return diagnostics


def has_valid_model_artifacts(path: Path) -> bool:
    info = model_artifact_diagnostics(path)
    return bool(
        info["exists"]
        and info["is_dir"]
        and info["config_json_exists"]
        and info["config_json_parseable"]
        and info["config_model_type_present"]
        and info["tokenizer_files_present"]
        and info["weight_files_present"]
    )


def local_model_dir(project_root: Path, model_id: str) -> Path:
    model_slug = model_id.replace("/", "--")
    return (project_root / "instance" / "models" / model_slug).resolve()


class AIModelArtifactOps:
    @staticmethod
    def model_artifact_diagnostics(path: Path) -> dict[str, Any]:
        return model_artifact_diagnostics(path)

    @staticmethod
    def has_valid_model_artifacts(path: Path) -> bool:
        return has_valid_model_artifacts(path)

    @staticmethod
    def local_model_dir(project_root: Path, model_id: str) -> Path:
        return local_model_dir(project_root, model_id)
