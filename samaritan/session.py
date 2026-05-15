"""Conversation persistence to ~/.samaritan/sessions/.

Each session is a JSON file containing the message history, accumulated
usage, the active mode, and a created/updated timestamp. After every
agent turn the active session is auto-saved; on startup the most recent
session can be auto-loaded if SAMARITAN_AUTOLOAD=1.

The SDK returns Pydantic content-block objects in `response.content`; to
round-trip them through JSON we coerce to dicts on save and the API
accepts dicts on load.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from samaritan.cost import Usage

_DIR = Path(os.path.expanduser("~/.samaritan/sessions"))


class Session:
    def __init__(self, session_id: str | None = None, mode: str = "samaritan"):
        self.id: str = session_id or _new_id()
        self.created_at: float = time.time()
        self.updated_at: float = self.created_at
        self.mode: str = mode
        self.messages: list[dict[str, Any]] = []
        self.usage: Usage = Usage()

    @property
    def path(self) -> Path:
        return _DIR / f"{self.id}.json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "mode": self.mode,
            "messages": [_jsonify(m) for m in self.messages],
            "usage": self.usage.__dict__,
        }

    def save(self) -> None:
        self.updated_at = time.time()
        try:
            _DIR.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
            )
            tmp.replace(self.path)
        except OSError:
            # Persistence failure must not break the session.
            pass

    @classmethod
    def load(cls, session_id: str) -> "Session | None":
        path = _DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        s = cls(session_id=data.get("id", session_id), mode=data.get("mode", "samaritan"))
        s.created_at = data.get("created_at", time.time())
        s.updated_at = data.get("updated_at", s.created_at)
        s.messages = data.get("messages", [])
        u = data.get("usage", {})
        s.usage = Usage(
            input_tokens=int(u.get("input_tokens", 0)),
            output_tokens=int(u.get("output_tokens", 0)),
            cache_creation_input_tokens=int(u.get("cache_creation_input_tokens", 0)),
            cache_read_input_tokens=int(u.get("cache_read_input_tokens", 0)),
        )
        return s


def list_sessions(limit: int = 20) -> list[tuple[str, float, int]]:
    """Return [(id, updated_at, message_count), ...] newest first."""
    if not _DIR.exists():
        return []
    items: list[tuple[str, float, int]] = []
    for p in _DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            items.append(
                (
                    data.get("id", p.stem),
                    data.get("updated_at", p.stat().st_mtime),
                    len(data.get("messages", [])),
                )
            )
        except (OSError, json.JSONDecodeError):
            continue
    items.sort(key=lambda t: t[1], reverse=True)
    return items[:limit]


def latest_session_id() -> str | None:
    items = list_sessions(limit=1)
    return items[0][0] if items else None


def _new_id() -> str:
    return f"sesn_{int(time.time())}_{uuid.uuid4().hex[:6]}"


def _jsonify(msg: dict[str, Any]) -> dict[str, Any]:
    """Convert a message that may contain Pydantic content blocks into a dict."""
    content = msg.get("content")
    if isinstance(content, str):
        return {"role": msg["role"], "content": content}
    if isinstance(content, list):
        return {
            "role": msg["role"],
            "content": [_jsonify_block(b) for b in content],
        }
    return msg


def _jsonify_block(block: Any) -> Any:
    if isinstance(block, dict):
        return block
    # Pydantic content block — use model_dump if available
    dump = getattr(block, "model_dump", None)
    if callable(dump):
        return dump(exclude_none=True)
    # Last-ditch: serialize via __dict__
    return dict(getattr(block, "__dict__", {}))
