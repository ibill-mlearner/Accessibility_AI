#!/usr/bin/env python3
"""Repository-level backend launcher.

This wrapper lets contributors run `python manage.py` from the repository root
while preserving the existing backend entrypoint in `AccessBackEnd/manage.py`.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    backend_dir = repo_root / "AccessBackEnd"
    backend_manage = backend_dir / "manage.py"

    if not backend_manage.exists():
        raise FileNotFoundError(f"Backend entrypoint not found: {backend_manage}")

    # Ensure backend imports work exactly as if launched inside AccessBackEnd.
    sys.path.insert(0, str(backend_dir))
    os.chdir(backend_dir)
    sys.argv[0] = str(backend_manage)
    runpy.run_path(str(backend_manage), run_name="__main__")


if __name__ == "__main__":
    main()
