from __future__ import annotations

import json
import os
from typing import Any, Callable

Cast = Callable[[Any], Any]


class EnvConfigError(ValueError):
    """Backward-compatible alias for config parse issues."""


def parse_env(key: str, default: Any = None, cast: Cast | None = None) -> Any:
    value = os.getenv(key, default)
    if value is None or cast is None:
        return value
    return cast(value)


def parse_positive_int(key: str, default: int) -> int:
    return int(parse_env(key, default, int))


def parse_json_object(key: str, default: dict[str, Any] | None = None) -> dict[str, Any] | None:
    raw = os.getenv(key)
    if raw is None:
        return default
    if not raw:
        return default
    parsed = json.loads(raw)
    if parsed is None:
        return default
    return parsed


def parse_csv_words(value: str) -> list[str]:
    return str(value).split()
