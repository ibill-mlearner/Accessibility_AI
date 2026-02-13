from __future__ import annotations

import sys
from pathlib import Path


# Keep the ai_pipeline test unit self-contained by wiring module imports locally.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
