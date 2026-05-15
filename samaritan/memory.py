"""Persistent memory: a small JSON store the assistant can read and write.

Bounded by design — the model cannot grow this without limit:
  - max 200 entries
  - max 8 KB per value
  - max 64 chars per key
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_DIR = Path(os.path.expanduser("~/.samaritan"))
_STORE = _DIR / "memory.json"

MAX_ENTRIES = 200
MAX_VALUE_BYTES = 8 * 1024
MAX_KEY_LEN = 64


def _load() -> dict[str, Any]:
    if not _STORE.exists():
        return {"facts": {}, "log": []}
    try:
        return json.loads(_STORE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"facts": {}, "log": []}


def _save(data: dict[str, Any]) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def remember(key: str, value: str) -> str:
    if not key:
        return "Refusing: empty key."
    if len(key) > MAX_KEY_LEN:
        return f"Refusing: key longer than {MAX_KEY_LEN} characters."
    if len(value.encode("utf-8")) > MAX_VALUE_BYTES:
        return f"Refusing: value larger than {MAX_VALUE_BYTES} bytes."
    data = _load()
    facts = data.setdefault("facts", {})
    if key not in facts and len(facts) >= MAX_ENTRIES:
        return (
            f"Refusing: memory store at capacity ({MAX_ENTRIES} entries). "
            "Forget something first."
        )
    facts[key] = value
    data.setdefault("log", []).append({"t": time.time(), "op": "set", "key": key})
    _save(data)
    return f"Stored: {key} = {value}"


def recall(key: str | None = None) -> str:
    data = _load()
    facts = data.get("facts", {})
    if not facts:
        return "Memory store is empty."
    if key:
        v = facts.get(key)
        return f"{key} = {v}" if v is not None else f"No entry for '{key}'."
    return "\n".join(f"{k}: {v}" for k, v in sorted(facts.items()))


def forget(key: str) -> str:
    data = _load()
    if key not in data.get("facts", {}):
        return f"No entry for '{key}'."
    del data["facts"][key]
    data.setdefault("log", []).append({"t": time.time(), "op": "del", "key": key})
    _save(data)
    return f"Removed: {key}"
