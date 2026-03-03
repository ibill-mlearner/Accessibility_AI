from __future__ import annotations

import os
import sys

# Guard against local module shadowing when this script is run from inside
# app/services/ai_pipeline (there is a sibling types.py that can shadow the
# Python stdlib "types" module used by argparse dependencies on Windows).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CWD = os.path.abspath(os.getcwd())
sys.path = [
    entry
    for entry in sys.path
    if os.path.abspath(entry or _CWD) != _SCRIPT_DIR
]

import argparse
import shutil
from pathlib import Path

DEFAULT_MODELS: dict[str, str] = {
    "qwen2.5": "Qwen/Qwen2.5-3B-Instruct",
    "llama3.2": "meta-llama/Llama-3.2-3B-Instruct",
    "gemma3": "google/gemma-3-4b-it",
    "phi4-mini": "microsoft/Phi-4-mini-instruct",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download starter LLMs into the local models folder for the AI pipeline."
        )
    )
    parser.add_argument(
        "--models-dir",
        default=None,
        help="Target models directory (default: AccessBackEnd/instance/models).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip downloads when target alias directory already exists.",
    )
    return parser.parse_args()


def resolve_default_models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "instance" / "models"


def ensure_hf_dependencies() -> tuple:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "huggingface_hub is required. Install it with: pip install huggingface_hub"
        ) from exc

    return snapshot_download


def download_model(
    *,
    alias: str,
    repo_id: str,
    models_dir: Path,
    snapshot_download,
    skip_existing: bool,
) -> None:
    target_dir = models_dir / alias
    if skip_existing and target_dir.exists():
        print(f"[skip] {alias}: directory already exists at {target_dir}")
        return

    print(f"[download] {alias} -> {repo_id}")
    snapshot_path = Path(
        snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
        )
    )

    if snapshot_path != target_dir:
        target_dir.mkdir(parents=True, exist_ok=True)
        for child in snapshot_path.iterdir():
            destination = target_dir / child.name
            if destination.exists():
                continue
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)

    print(f"[ok] {alias} downloaded to {target_dir}")


def main() -> None:
    args = parse_args()
    snapshot_download = ensure_hf_dependencies()

    models_dir = (
        Path(args.models_dir).expanduser().resolve()
        if args.models_dir
        else resolve_default_models_dir().resolve()
    )
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using models directory: {models_dir}")
    for alias, repo_id in DEFAULT_MODELS.items():
        download_model(
            alias=alias,
            repo_id=repo_id,
            models_dir=models_dir,
            snapshot_download=snapshot_download,
            skip_existing=args.skip_existing,
        )

    print("All requested models processed.")


if __name__ == "__main__":
    main()