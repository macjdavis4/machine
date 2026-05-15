"""Samaritan-style terminal rendering.

The visual language of Samaritan from Person of Interest: monochromatic cyan/teal
text on black, classification banners, fixed-width data readouts, and a tone of
detached surveillance-grade observation. Jarvis provides the personality; this
module provides the cold, observational *display*.
"""

from __future__ import annotations

import os
import platform
import socket
import time
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

CYAN = "bright_cyan"
DIM_CYAN = "cyan"
RED = "bright_red"
AMBER = "yellow"
DARK = "grey15"

console = Console(highlight=False, soft_wrap=False)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _host_id() -> str:
    try:
        return socket.gethostname().upper()
    except Exception:
        return "UNKNOWN-NODE"


def _platform_id() -> str:
    return f"{platform.system().upper()} {platform.release()}"


def boot_sequence() -> None:
    """Cold-boot identification ritual. Brief, deliberate, no flourish."""
    lines = [
        ("> INITIALIZING ANALYSIS ENGINE", 0.18),
        ("> ACCESSING LOCAL MEMORY                              [ OK ]", 0.10),
        ("> ESTABLISHING UPLINK ─ ANTHROPIC/CLAUDE-OPUS-4-7     [ OK ]", 0.10),
        ("> AUDIO INTERFACE                                     [ OK ]", 0.08),
        ("> MESSAGE ARCHIVE ACCESS                              [ OK ]", 0.08),
        ("> CALENDAR INTERFACE                                  [ OK ]", 0.08),
        ("> NOTES INTERFACE                                     [ OK ]", 0.08),
        ("> SYSTEM ACTIVE.", 0.20),
    ]
    for text, delay in lines:
        console.print(Text(text, style=CYAN))
        time.sleep(delay)


def classification_banner() -> None:
    """The persistent header — Samaritan's classification readout."""
    user = os.environ.get("SAMARITAN_USER_NAME", "PRIMARY ASSET")
    header = Text()
    header.append("▌ ", style=CYAN)
    header.append("SAMARITAN", style=f"bold {CYAN}")
    header.append("  ◆  ", style=DIM_CYAN)
    header.append("ANALYSIS ACTIVE", style=CYAN)
    header.append("  ◆  ", style=DIM_CYAN)
    header.append(f"OPERATOR: {user.upper()}", style=CYAN)

    meta = Text()
    meta.append(f"NODE {_host_id()}", style=DIM_CYAN)
    meta.append("  │  ", style=DARK)
    meta.append(_platform_id(), style=DIM_CYAN)
    meta.append("  │  ", style=DARK)
    meta.append(_utc_stamp(), style=DIM_CYAN)

    console.print(Rule(style=DIM_CYAN))
    console.print(header)
    console.print(meta)
    console.print(Rule(style=DIM_CYAN))


def prompt_input() -> str:
    """Read a line of input with a Samaritan-style prompt."""
    console.print()
    label = Text()
    label.append("▸ QUERY  ", style=f"bold {CYAN}")
    label.append("» ", style=DIM_CYAN)
    console.print(label, end="")
    try:
        return input()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return "/exit"


def render_thinking(text: str) -> None:
    """Render an extended-thinking summary block, dimmer than primary output."""
    if not text.strip():
        return
    panel = Panel(
        Text(text.strip(), style=DIM_CYAN),
        title="[bold cyan]◆ COGITATION[/bold cyan]",
        title_align="left",
        border_style=DIM_CYAN,
        padding=(0, 1),
    )
    console.print(panel)


def render_response(text: str) -> None:
    """Render the assistant's primary text response."""
    if not text.strip():
        return
    panel = Panel(
        Text(text.strip(), style=CYAN),
        title="[bold bright_cyan]▶ TRANSMISSION[/bold bright_cyan]",
        title_align="left",
        border_style=CYAN,
        padding=(0, 1),
    )
    console.print(panel)


def render_tool_call(name: str, params: dict) -> None:
    """Show a tool call as a surveillance event log line."""
    line = Text()
    line.append("● ", style=AMBER)
    line.append("SUBROUTINE  ", style=f"bold {AMBER}")
    line.append(name, style=CYAN)
    line.append("  ", style=DARK)
    if params:
        keys = ", ".join(f"{k}={_short(v)}" for k, v in params.items())
        line.append(f"[{keys}]", style=DIM_CYAN)
    console.print(line)


def render_tool_result(name: str, result: str, is_error: bool = False) -> None:
    """Show the result of a tool call, truncated for the operator's display."""
    color = RED if is_error else DIM_CYAN
    label = "FAULT" if is_error else "RETURN"
    line = Text()
    line.append("  ↳ ", style=color)
    line.append(f"{label}  ", style=f"bold {color}")
    line.append(_short(result, limit=140), style=color)
    console.print(line)


def render_system_message(text: str, level: str = "info") -> None:
    color = {"info": DIM_CYAN, "warn": AMBER, "error": RED}.get(level, DIM_CYAN)
    console.print(Text(f"⟡ {text}", style=color))


def render_directive(text: str) -> None:
    """One-line directive output (used for short acknowledgements)."""
    console.print(Text(f"▶ {text}", style=f"bold {CYAN}"))


def goodbye() -> None:
    console.print()
    console.print(Rule(style=DIM_CYAN))
    console.print(Text("▌ SAMARITAN ─ SESSION TERMINATED. STANDING DOWN.", style=CYAN))
    console.print(Rule(style=DIM_CYAN))


def _short(value, limit: int = 60) -> str:
    s = str(value).replace("\n", " ⏎ ")
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


__all__ = [
    "boot_sequence",
    "classification_banner",
    "console",
    "goodbye",
    "prompt_input",
    "render_directive",
    "render_response",
    "render_system_message",
    "render_thinking",
    "render_tool_call",
    "render_tool_result",
]
