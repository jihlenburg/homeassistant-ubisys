"""Elegant, consistent logging utilities for the Ubisys integration.

Provides banner-style summaries and compact key=value formatting so logs are
easy to scan in Home Assistant.
"""

from __future__ import annotations

import logging
import time
from typing import Any


def _fmt_kv(**kvs: Any) -> str:
    """Format key=value pairs in a stable, compact way."""
    parts: list[str] = []
    for k in sorted(kvs.keys()):
        v = kvs[k]
        parts.append(f"{k}={v}")
    return ", ".join(parts)


def info_banner(logger: logging.Logger, title: str, **kvs: Any) -> None:
    """Log a 3‑line banner with an optional key=value summary at INFO level."""
    line = _fmt_kv(**kvs) if kvs else ""
    logger.info("╔%s╗", "═" * max(1, len(title) + (len(line) + 2 if line else 0)))
    if line:
        logger.info("║  %s  %s", title, line)
    else:
        logger.info("║  %s", title)
    logger.info("╚%s╝", "═" * max(1, len(title) + (len(line) + 2 if line else 0)))


def kv(logger: logging.Logger, level: int, msg: str, **kvs: Any) -> None:
    """Log a message followed by stable key=value pairs at the given level.

    Avoids formatting cost when the logger is not enabled for the level.
    """
    if not logger.isEnabledFor(level):
        return
    if kvs:
        logger.log(level, "%s — %s", msg, _fmt_kv(**kvs))
    else:
        logger.log(level, "%s", msg)


class Stopwatch:
    """Simple stopwatch to measure elapsed time for operations."""

    def __init__(self) -> None:
        self._start = time.time()

    @property
    def elapsed(self) -> float:
        return time.time() - self._start
