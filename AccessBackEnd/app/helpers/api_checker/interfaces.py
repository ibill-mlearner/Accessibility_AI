from __future__ import annotations

from typing import Any, Callable, Protocol


class RecordLike(Protocol):
    """Minimal protocol for ORM-ish records used by API serializers."""

    id: int


Payload = dict[str, Any]
SerializerFn = Callable[[Any], Payload]