from __future__ import annotations

import logging


# Handoff note: `logging.basicConfig(...)` sets process-wide level + log-line structure
# (timestamp, level, logger name, message) expected by route/service instrumentation.
def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
