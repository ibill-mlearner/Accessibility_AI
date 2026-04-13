from __future__ import annotations

import argparse
import json
import sys
import traceback
from time import perf_counter

import ai_pipeline
from ai_pipeline import AIPipelineInterface


def run_download_demo(model_id: str) -> int:
    """Download model artifacts and print payload + timing."""
    api = AIPipelineInterface()

    started_at = perf_counter()
    try:
        service = api.AIPipelineModelDownloadService()
        payload = service.download(model_id=model_id, provider="huggingface")
    except AttributeError:
        model_loader = ai_pipeline.ModelLoader(
            model_name=model_id,
            device_map=None,
            torch_dtype="auto",
            download_locally=True,
        )
        tokenizer_loader = ai_pipeline.TokenizerLoader(
            model_name=model_id,
            download_locally=True,
        )
        model_loader.build()
        tokenizer_loader.build()
        payload = {"provider": "huggingface", "model_id": model_id, "status": "downloaded"}
    elapsed_seconds = perf_counter() - started_at

    print("=== Download payload ===")
    print(json.dumps(payload, indent=2))
    print(f"Elapsed: {elapsed_seconds:.2f}s")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone ai_pipeline model download probe.")
    parser.add_argument(
        "--model-id",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Hugging Face model id to download.",
    )
    args = parser.parse_args()

    try:
        return run_download_demo(model_id=str(args.model_id))
    except Exception as exc:  # noqa: BLE001 - explicit standalone troubleshooting output.
        print("=== Download demo failed ===", file=sys.stderr)
        print(f"ai_pipeline_path={getattr(ai_pipeline, '__file__', 'unknown')}", file=sys.stderr)
        print(f"ai_pipeline_exports_sample={[name for name in dir(ai_pipeline) if 'Download' in name][:10]}", file=sys.stderr)
        print(f"error_type={type(exc).__name__}", file=sys.stderr)
        print(f"error={exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())