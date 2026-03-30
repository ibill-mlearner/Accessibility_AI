#!/usr/bin/env python3
"""Runtime probe for backend container hardware acceleration status."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def _run_nvidia_smi() -> dict:
    if shutil.which("nvidia-smi") is None:
        return {
            "available": False,
            "reason": "nvidia-smi not found in container PATH",
        }

    cmd = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "available": False,
            "reason": result.stderr.strip() or "nvidia-smi returned non-zero status",
        }

    gpus = []
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 4:
            gpus.append(
                {
                    "name": parts[0],
                    "memory_total_mb": parts[1],
                    "memory_free_mb": parts[2],
                    "driver_version": parts[3],
                }
            )

    return {"available": bool(gpus), "gpus": gpus}


def _run_torch_probe() -> dict:
    try:
        import torch  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover
        return {"importable": False, "error": str(exc)}

    cuda_available = torch.cuda.is_available()
    payload = {
        "importable": True,
        "version": getattr(torch, "__version__", "unknown"),
        "cuda_available": cuda_available,
        "cuda_device_count": torch.cuda.device_count() if cuda_available else 0,
    }

    if cuda_available:
        payload["device_names"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]

    return payload


def main() -> int:
    report = {
        "nvidia_smi": _run_nvidia_smi(),
        "torch": _run_torch_probe(),
    }
    print(json.dumps(report, indent=2))

    smi_ok = report["nvidia_smi"].get("available", False)
    torch_ok = report["torch"].get("cuda_available", False)
    return 0 if smi_ok and torch_ok else 1


if __name__ == "__main__":
    sys.exit(main())
