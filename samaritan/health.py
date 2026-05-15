"""Startup health checks — surface what's reachable before the operator
starts asking the model to do things.

Each check is fast (≤ 300 ms typical), non-blocking on failure, and returns
a tuple of (label, status, detail). Status is one of "ok", "warn", "fail".
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

import anthropic


def _check_api_key() -> tuple[str, str, str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return ("api key", "fail", "ANTHROPIC_API_KEY not set")
    if not key.startswith("sk-"):
        return ("api key", "warn", "key does not look like an Anthropic key")
    return ("api key", "ok", f"sk-…{key[-4:]}")


def _check_api_reachable() -> tuple[str, str, str]:
    try:
        client = anthropic.Anthropic(timeout=5.0, max_retries=0)
        client.models.retrieve("claude-opus-4-7")
    except anthropic.AuthenticationError:
        return ("anthropic api", "fail", "authentication rejected")
    except anthropic.APIConnectionError as exc:
        # Transient — let the operator start and surface real errors per turn.
        return ("anthropic api", "warn", f"no connection: {exc}")
    except anthropic.APIStatusError as exc:
        return ("anthropic api", "warn", f"status {exc.status_code}")
    except Exception as exc:  # noqa: BLE001
        return ("anthropic api", "warn", f"{type(exc).__name__}: {exc}")
    return ("anthropic api", "ok", "claude-opus-4-7 reachable")


def _check_messages_db() -> tuple[str, str, str]:
    path = Path(os.path.expanduser("~/Library/Messages/chat.db"))
    if not path.exists():
        return ("imessages", "warn", "chat.db not present (not macOS or not signed in)")
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, timeout=2)
        conn.execute("SELECT COUNT(*) FROM message LIMIT 1").fetchone()
        conn.close()
    except sqlite3.OperationalError:
        return ("imessages", "fail", "denied — grant Full Disk Access to your terminal")
    return ("imessages", "ok", str(path))


def _check_osascript() -> tuple[str, str, str]:
    if not shutil.which("osascript"):
        return ("osascript", "warn", "not found (Notes / Calendar / Reminders unavailable)")
    return ("osascript", "ok", "available")


def _check_say() -> tuple[str, str, str]:
    if not shutil.which("say"):
        return ("voice synth", "warn", "`say` not found (TTS unavailable)")
    return ("voice synth", "ok", os.environ.get("SAMARITAN_VOICE", "Daniel"))


def _check_clipboard() -> tuple[str, str, str]:
    has_copy = shutil.which("pbcopy") is not None
    has_paste = shutil.which("pbpaste") is not None
    if has_copy and has_paste:
        return ("clipboard", "ok", "pbcopy/pbpaste available")
    return ("clipboard", "warn", "pbcopy/pbpaste not found")


def run_checks(skip_network: bool = False) -> list[tuple[str, str, str]]:
    checks = [
        _check_api_key(),
    ]
    if not skip_network:
        checks.append(_check_api_reachable())
    checks.extend(
        [
            _check_messages_db(),
            _check_osascript(),
            _check_say(),
            _check_clipboard(),
        ]
    )
    return checks


def has_blocking_failures(checks: list[tuple[str, str, str]]) -> bool:
    """Anthropic API access is the only hard requirement."""
    for label, status, _detail in checks:
        if status == "fail" and label in ("api key", "anthropic api"):
            return True
    return False
