"""Runtime mode state — selects Jarvis or Samaritan persona + UI.

Two modes:
  - "jarvis"    Stark-Industries holographic blue HUD + warm British butler voice.
  - "samaritan" Surveillance-cyan classification HUD + cold observational voice.

Default is read from $SAMARITAN_MODE, falling back to a persisted choice in
~/.samaritan/mode, falling back to "samaritan".
"""

from __future__ import annotations

import os
from pathlib import Path

_VALID = ("jarvis", "samaritan")
_STATE_FILE = Path(os.path.expanduser("~/.samaritan/mode"))
_current: str | None = None


def _read_persisted() -> str | None:
    if not _STATE_FILE.exists():
        return None
    try:
        val = _STATE_FILE.read_text().strip().lower()
    except OSError:
        return None
    return val if val in _VALID else None


def _initial() -> str:
    env = os.environ.get("SAMARITAN_MODE", "").strip().lower()
    if env in _VALID:
        return env
    return _read_persisted() or "samaritan"


def current() -> str:
    global _current
    if _current is None:
        _current = _initial()
    return _current


def set_mode(mode: str) -> str:
    """Set the active mode. Returns the normalized mode name."""
    global _current
    mode = mode.strip().lower()
    if mode not in _VALID:
        raise ValueError(
            f"Unknown mode '{mode}'. Choose one of: {', '.join(_VALID)}"
        )
    _current = mode
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(mode + "\n")
    except OSError:
        pass  # persistence is best-effort
    return mode


def is_jarvis() -> bool:
    return current() == "jarvis"


def is_samaritan() -> bool:
    return current() == "samaritan"
