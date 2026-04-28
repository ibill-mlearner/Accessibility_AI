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


class AIModelArtifactOps:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.config_file = path / "config.json"

    def model_artifact_diagnostics(self) -> dict[str, Any]:
        diagnostics: dict[str, Any] = {
            "resolved_model_dir": str(self.path),
            "exists": self.path.exists(),
            "is_dir": self.path.is_dir(),
            "config_json_exists": self.config_file.exists(),
            "config_json_parseable": False,
            "config_model_type_present": False,
            "tokenizer_files_present": False,
            "tokenizer_files_found": [],
            "weight_files_present": False,
            "weight_files_found": [],
            "directory_listing": [],
        }

        if self.path.exists() and self.path.is_dir():
            diagnostics["directory_listing"] = sorted(child.name for child in self.path.iterdir())[:20]

        if self.config_file.exists() and self.config_file.is_file():
            try:
                config_payload = json.loads(self.config_file.read_text(encoding="utf-8"))
                diagnostics["config_json_parseable"] = isinstance(config_payload, dict)
                diagnostics["config_model_type_present"] = isinstance(config_payload, dict) and bool(config_payload.get("model_type"))
            except Exception:
                diagnostics["config_json_parseable"] = False

        found_tokenizers = [name for name in _TOKENIZER_CANDIDATES if (self.path / name).exists()]
        diagnostics["tokenizer_files_found"] = found_tokenizers
        diagnostics["tokenizer_files_present"] = bool(found_tokenizers)

        found_weights = [name for name in _WEIGHT_CANDIDATES if (self.path / name).exists()]
        diagnostics["weight_files_found"] = found_weights
        diagnostics["weight_files_present"] = bool(found_weights)
        return diagnostics

    @staticmethod
    def diagnostics_for_path(path: Path) -> dict[str, Any]:
        return AIModelArtifactOps(path).model_artifact_diagnostics()

    def has_valid_model_artifacts(self) -> bool:
        info = self.model_artifact_diagnostics()
        return bool(
            info["exists"]
            and info["is_dir"]
            and info["config_json_exists"]
            and info["config_json_parseable"]
            and info["config_model_type_present"]
            and info["tokenizer_files_present"]
            and info["weight_files_present"]
        )

    @staticmethod
    def has_valid_artifacts_for_path(path: Path) -> bool:
        return AIModelArtifactOps(path).has_valid_model_artifacts()

    @staticmethod
    def local_model_dir(project_root: Path, model_id: str) -> Path:
        model_slug = model_id.replace("/", "--")
        return (project_root / "instance" / "models" / model_slug).resolve()
