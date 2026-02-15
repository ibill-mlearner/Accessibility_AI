from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Protocol

MAX_LOG_LINES = 2000
DEFAULT_LOG_BASENAME = "ai_interactions"


class InteractionRunner(Protocol):
    def run_interaction(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class RotatingTextLogWriter:
    log_dir: Path
    base_name: str = DEFAULT_LOG_BASENAME
    max_lines: int = MAX_LOG_LINES
    _lock: Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, line: str) -> None:
        with self._lock:
            target = self._current_file()
            if self._line_count(target) >= self.max_lines:
                target = self._next_file(target)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(f"{line}\n")

    def _line_count(self, path: Path) -> int:
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)

    def _current_file(self) -> Path:
        files = sorted(self.log_dir.glob(f"{self.base_name}_*.txt"))
        if not files:
            return self.log_dir / f"{self.base_name}_1.txt"
        return files[-1]

    def _next_file(self, current: Path) -> Path:
        suffix = current.stem.rsplit("_", 1)[-1]
        next_index = int(suffix) + 1 if suffix.isdigit() else 1
        return self.log_dir / f"{self.base_name}_{next_index}.txt"


class InteractionLoggingService:
    """Observer-style wrapper that logs interaction metadata to rotating text files."""

    def __init__(self, wrapped: InteractionRunner, writer: RotatingTextLogWriter) -> None:
        self._wrapped = wrapped
        self._writer = writer

    def run_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        *,
        initiated_by: str = "anonymous",
    ) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        status = "success"

        try:
            response = self._wrapped.run_interaction(prompt=prompt, context=context)
            return response
        except Exception:
            status = "failed"
            raise
        finally:
            context_payload = context if isinstance(context, dict) else {}
            payload = {
                "timestamp": started_at.isoformat(),
                "initiated_by": initiated_by,
                "status": status,
                "prompt_preview": (prompt or "")[:120],
                "context": context_payload,
            }
            self._writer.append(json.dumps(payload, default=str, sort_keys=True))
