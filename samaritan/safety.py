"""Tool safety: denylist, confirmation gates, output capping.

Read-only tools run silently. Destructive or outbound tools (those that
mutate the operator's data, leave the device, or interact with the
physical world) prompt for explicit confirmation before executing.

Configure via env:
    SAMARITAN_DISABLE_TOOLS    comma-separated tool names to refuse outright
    SAMARITAN_AUTO_APPROVE     '1' to skip confirmation prompts (dangerous)
    SAMARITAN_MAX_TOOL_OUTPUT  bytes to cap tool result strings at (default 8192)
"""

from __future__ import annotations

import os
from typing import Iterable

# Tools that *write* or *transmit* — require operator approval each call.
CONFIRM_TOOLS: frozenset[str] = frozenset(
    {
        "create_apple_note",
        "append_to_apple_note",
        "speak",
        "open_url",
        "set_reminder",
        "music_control",
        "clipboard_write",
        "forget_fact",
    }
)


def disabled_tools() -> frozenset[str]:
    raw = os.environ.get("SAMARITAN_DISABLE_TOOLS", "")
    return frozenset(t.strip() for t in raw.split(",") if t.strip())


def is_disabled(name: str) -> bool:
    return name in disabled_tools()


def needs_confirmation(name: str) -> bool:
    if os.environ.get("SAMARITAN_AUTO_APPROVE") == "1":
        return False
    return name in CONFIRM_TOOLS


def max_tool_output_bytes() -> int:
    try:
        return max(512, int(os.environ.get("SAMARITAN_MAX_TOOL_OUTPUT", "8192")))
    except ValueError:
        return 8192


def cap_output(text: str) -> tuple[str, bool]:
    """Trim a tool result to the configured byte cap.

    Returns (capped_text, was_truncated).
    """
    limit = max_tool_output_bytes()
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    # Truncate by bytes, then re-decode safely, then mark truncation
    truncated = encoded[:limit].decode("utf-8", errors="ignore")
    note = f"\n\n[output truncated — {len(encoded)} bytes capped at {limit}]"
    return truncated + note, True


def render_disabled_response(name: str) -> str:
    return f"Tool '{name}' is disabled by operator policy (SAMARITAN_DISABLE_TOOLS)."


def render_denied_response(name: str) -> str:
    return f"Operator denied execution of '{name}'."
