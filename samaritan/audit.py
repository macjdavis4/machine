"""JSONL audit log of every tool invocation.

One line per call to ~/.samaritan/audit.log. The result body is hashed, not
written, so the log is small and PII-resistant.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

_LOG = Path(os.path.expanduser("~/.samaritan/audit.log"))
_MAX_BYTES = 5 * 1024 * 1024  # rotate at 5 MB


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _rotate_if_needed() -> None:
    try:
        if _LOG.exists() and _LOG.stat().st_size > _MAX_BYTES:
            _LOG.rename(_LOG.with_suffix(".log.1"))
    except OSError:
        pass


def record(
    tool: str,
    params: dict[str, Any],
    result: str,
    *,
    is_error: bool = False,
    elapsed_ms: int | None = None,
) -> None:
    entry = {
        "t": time.time(),
        "tool": tool,
        "params": _safe_params(params),
        "result_sha": _hash(result),
        "result_len": len(result),
        "is_error": is_error,
    }
    if elapsed_ms is not None:
        entry["elapsed_ms"] = elapsed_ms
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed()
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # Audit log failure must not break the session.
        pass


def _safe_params(params: dict[str, Any]) -> dict[str, Any]:
    """Cap any string value at 200 chars so the log stays compact."""
    out: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 200:
            out[k] = v[:200] + "…"
        else:
            out[k] = v
    return out
