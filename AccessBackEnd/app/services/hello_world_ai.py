"""Standalone demo script for the AI pipeline package.

Run from the backend folder:
    python app/services/hello_world_ai.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
INSTANCE_DIR = BACKEND_ROOT / "app" / "instance"
DEMO_MODEL_REPO_ID = os.getenv("AI_DEMO_MODEL_REPO", "NousResearch/Meta-Llama-3-8B-Instruct")
DEMO_MODEL_LOCAL_DIR = INSTANCE_DIR / "models" / "meta-llama-3-8b-instruct"


def _configure_import_path() -> None:
    """Ensure standalone execution resolves stdlib modules before local packages.

    Running this file directly adds ``app/services`` to ``sys.path[0]`` which can
    accidentally shadow Python's standard-library ``logging`` module with
    ``app/services/logging``. That collision breaks Flask/Werkzeug imports.

    This keeps backend-root imports available while removing the script directory
    from import resolution precedence.
    """

    script_dir = str(SCRIPT_DIRECTORY)
    while script_dir in sys.path:
        sys.path.remove(script_dir)

    backend_root = str(BACKEND_ROOT)
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)


def ensure_demo_model() -> Path:
    """Ensure an 8B model exists under ``app/instance`` for demo inference."""

    DEMO_MODEL_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    if (DEMO_MODEL_LOCAL_DIR / "config.json").exists():
        return DEMO_MODEL_LOCAL_DIR

    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # pragma: no cover - env specific
        raise RuntimeError(
            "huggingface_hub is required. Install backend requirements to run the AI demo."
        ) from exc

    snapshot_download(
        repo_id=DEMO_MODEL_REPO_ID,
        local_dir=DEMO_MODEL_LOCAL_DIR,
        local_dir_use_symlinks=False,
    )
    return DEMO_MODEL_LOCAL_DIR


_configure_import_path()

from app.services.ai_pipeline import AIPipelineConfig, AIPipelineService


DEFAULT_SYSTEM_PROMPT = (
    "You are Access AI assistant. Follow accessibility-first guidance and return concise, actionable support."
)


def build_prompt_with_system_instructions(system_prompt: str, user_prompt: str) -> str:
    """Rough-in system prompt composition for sprint-level experimentation.

    Current AI pipeline entry point accepts a single `prompt` string.
    This helper demonstrates how system instructions can be prepended while
    preserving the existing pipeline contract.
    """

    return f"System instructions:\n{system_prompt}\n\nUser request:\n{user_prompt}".strip()


def main() -> None:
    model_path = ensure_demo_model()

    pipeline = AIPipelineService(
        AIPipelineConfig(
            provider="huggingface",
            huggingface_model_id=str(model_path),
            max_new_tokens=192,
            temperature=0.2,
        )
    )

    user_prompt = "Generate accessibility support suggestions for a lecture chat tool."
    composed_prompt = build_prompt_with_system_instructions(DEFAULT_SYSTEM_PROMPT, user_prompt)

    context = {
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "sprint_note": "Demo uses a local 8B HuggingFace model in app/instance/models.",
    }

    response = pipeline.run_interaction(composed_prompt, context=context)

    print("=== Pipeline input payload (demo) ===")
    print(json.dumps({"prompt": composed_prompt, "context": context, "model_path": str(model_path)}, indent=2))
    print("\n=== Pipeline response ===")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
