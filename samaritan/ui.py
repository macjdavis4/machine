"""Terminal rendering — two visual languages, selected by current mode.

JARVIS  ─ holographic Stark-Industries palette: blue with amber accents.
SAMARITAN ─ surveillance HUD: cyan-on-black classification banner.

Each render function dispatches on `mode.current()` so swapping at runtime
is a single state change away. Includes streaming primitives that print
deltas directly to the terminal (rather than into a Panel) so the
typewriter effect is visible.
"""

from __future__ import annotations

import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from samaritan import mode

# Samaritan palette
S_PRIMARY = "bright_cyan"
S_DIM = "cyan"
S_WARN = "yellow"
S_ERROR = "bright_red"
S_DARK = "grey15"

# Jarvis palette — Stark-HUD holographic blue with reactor-amber accents
J_PRIMARY = "bright_blue"
J_DIM = "deep_sky_blue1"
J_ACCENT = "orange1"
J_WARN = "orange3"
J_ERROR = "bright_red"
J_DARK = "grey15"


console = Console(highlight=False, soft_wrap=False)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _host_id() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown-node"


def _platform_id() -> str:
    return f"{platform.system()} {platform.release()}"


# ─── BOOT ────────────────────────────────────────────────────────────────────

def boot_sequence() -> None:
    if mode.is_jarvis():
        lines = [
            ("> J.A.R.V.I.S. coming online.", 0.18),
            ("> Local sensors                                     [ nominal ]", 0.10),
            ("> Uplink ─ Anthropic / Claude Opus 4.7              [ engaged ]", 0.10),
            ("> Voice interface                                   [ ready   ]", 0.08),
            ("> Communications archive                            [ ready   ]", 0.08),
            ("> Scheduling interface                              [ ready   ]", 0.08),
            ("> Personal notes                                    [ ready   ]", 0.08),
            (f"> All systems at your disposal, {os.environ.get('SAMARITAN_USER_NAME', 'sir')}.", 0.20),
        ]
        color = J_PRIMARY
    else:
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
        color = S_PRIMARY

    for text, delay in lines:
        console.print(Text(text, style=color))
        time.sleep(delay)


# ─── HEADER ──────────────────────────────────────────────────────────────────

def classification_banner() -> None:
    if mode.is_jarvis():
        _jarvis_header()
    else:
        _samaritan_header()


def _jarvis_header() -> None:
    user = os.environ.get("SAMARITAN_USER_NAME", "Sir")
    header = Text()
    header.append("▽ ", style=J_ACCENT)
    header.append("J . A . R . V . I . S .", style=f"bold {J_PRIMARY}")
    header.append("   ", style=J_DARK)
    header.append("◇  at your service, ", style=J_DIM)
    header.append(user, style=f"bold {J_ACCENT}")
    header.append("  ◇", style=J_DIM)

    meta = Text()
    meta.append(f"{_host_id()}", style=J_DIM)
    meta.append("  ·  ", style=J_DARK)
    meta.append(_platform_id(), style=J_DIM)
    meta.append("  ·  ", style=J_DARK)
    meta.append(_utc_stamp(), style=J_DIM)

    console.print(Rule(style=J_DIM))
    console.print(header)
    console.print(meta)
    console.print(Rule(style=J_DIM))


def _samaritan_header() -> None:
    user = os.environ.get("SAMARITAN_USER_NAME", "PRIMARY ASSET")
    header = Text()
    header.append("▌ ", style=S_PRIMARY)
    header.append("SAMARITAN", style=f"bold {S_PRIMARY}")
    header.append("  ◆  ", style=S_DIM)
    header.append("ANALYSIS ACTIVE", style=S_PRIMARY)
    header.append("  ◆  ", style=S_DIM)
    header.append(f"OPERATOR: {user.upper()}", style=S_PRIMARY)

    meta = Text()
    meta.append(f"NODE {_host_id().upper()}", style=S_DIM)
    meta.append("  │  ", style=S_DARK)
    meta.append(_platform_id().upper(), style=S_DIM)
    meta.append("  │  ", style=S_DARK)
    meta.append(_utc_stamp(), style=S_DIM)

    console.print(Rule(style=S_DIM))
    console.print(header)
    console.print(meta)
    console.print(Rule(style=S_DIM))


# ─── INPUT ───────────────────────────────────────────────────────────────────

def prompt_input() -> str:
    console.print()
    if mode.is_jarvis():
        label = Text()
        label.append("▸ ", style=J_ACCENT)
        user = os.environ.get("SAMARITAN_USER_NAME", "Sir")
        label.append(f"{user}", style=f"bold {J_PRIMARY}")
        label.append(" » ", style=J_DIM)
    else:
        label = Text()
        label.append("▸ QUERY  ", style=f"bold {S_PRIMARY}")
        label.append("» ", style=S_DIM)
    console.print(label, end="")
    try:
        return input()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return "/exit"


def confirm_action(name: str, params: dict) -> bool:
    """Block on a yes/no confirmation prompt for a tool call."""
    console.print()
    if mode.is_jarvis():
        prompt = Text()
        prompt.append("◇ ", style=J_ACCENT)
        prompt.append("Permit ", style=f"bold {J_ACCENT}")
        prompt.append(name, style=J_PRIMARY)
        prompt.append("?  ", style=J_DIM)
        prompt.append("[y/N] ", style=J_ACCENT)
    else:
        prompt = Text()
        prompt.append("⚠ ", style=S_WARN)
        prompt.append("AUTHORIZE ", style=f"bold {S_WARN}")
        prompt.append(name, style=S_PRIMARY)
        prompt.append("  ", style=S_DARK)
        prompt.append("[y/N] ", style=S_WARN)
    console.print(prompt, end="")
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return False
    return answer in ("y", "yes")


# ─── STREAMING PRIMITIVES ────────────────────────────────────────────────────

_PRIMARY = lambda: J_PRIMARY if mode.is_jarvis() else S_PRIMARY  # noqa: E731
_DIM = lambda: J_DIM if mode.is_jarvis() else S_DIM  # noqa: E731
_ACCENT = lambda: J_ACCENT if mode.is_jarvis() else S_PRIMARY  # noqa: E731


def start_stream_block(kind: str) -> None:
    """Print a header line before a streamed thinking/text block begins."""
    console.print()
    if kind == "thinking":
        if mode.is_jarvis():
            line = Text("◇ Analysis ─", style=f"bold {J_ACCENT}")
        else:
            line = Text("◆ COGITATION ─", style=f"bold {S_PRIMARY}")
    else:  # text / response
        if mode.is_jarvis():
            line = Text("▸ Response ─", style=f"bold {J_PRIMARY}")
        else:
            line = Text("▶ TRANSMISSION ─", style=f"bold {S_PRIMARY}")
    console.print(line)


def stream_text(delta: str, kind: str = "text") -> None:
    """Write a delta of streamed text in the appropriate color, no newline."""
    if not delta:
        return
    style = _DIM() if kind == "thinking" else _PRIMARY()
    console.print(Text(delta, style=style), end="", soft_wrap=True)
    sys.stdout.flush()


def end_stream_block(kind: str) -> None:
    """Newline after a streamed block."""
    console.print()


# ─── NON-STREAM PANEL RENDERING (used outside the stream path) ───────────────

def render_thinking(text: str) -> None:
    if not text.strip():
        return
    if mode.is_jarvis():
        panel = Panel(
            Text(text.strip(), style=J_DIM),
            title=f"[bold {J_ACCENT}]◇ Analysis[/]",
            title_align="left",
            border_style=J_DIM,
            padding=(0, 1),
        )
    else:
        panel = Panel(
            Text(text.strip(), style=S_DIM),
            title=f"[bold {S_PRIMARY}]◆ COGITATION[/]",
            title_align="left",
            border_style=S_DIM,
            padding=(0, 1),
        )
    console.print(panel)


def render_response(text: str) -> None:
    if not text.strip():
        return
    if mode.is_jarvis():
        panel = Panel(
            Text(text.strip(), style=J_PRIMARY),
            title=f"[bold {J_PRIMARY}]▸ Response[/]",
            title_align="left",
            border_style=J_PRIMARY,
            padding=(0, 1),
        )
    else:
        panel = Panel(
            Text(text.strip(), style=S_PRIMARY),
            title=f"[bold {S_PRIMARY}]▶ TRANSMISSION[/]",
            title_align="left",
            border_style=S_PRIMARY,
            padding=(0, 1),
        )
    console.print(panel)


# ─── TOOL EVENTS ─────────────────────────────────────────────────────────────

def render_tool_call(name: str, params: dict) -> None:
    if mode.is_jarvis():
        line = Text()
        line.append("▸ ", style=J_ACCENT)
        line.append("Running  ", style=f"bold {J_ACCENT}")
        line.append(name, style=J_PRIMARY)
        if params:
            keys = ", ".join(f"{k}={_short(v)}" for k, v in params.items())
            line.append(f"  ({keys})", style=J_DIM)
    else:
        line = Text()
        line.append("● ", style=S_WARN)
        line.append("SUBROUTINE  ", style=f"bold {S_WARN}")
        line.append(name, style=S_PRIMARY)
        if params:
            keys = ", ".join(f"{k}={_short(v)}" for k, v in params.items())
            line.append(f"  [{keys}]", style=S_DIM)
    console.print(line)


def render_tool_result(name: str, result: str, is_error: bool = False) -> None:
    if mode.is_jarvis():
        color = J_ERROR if is_error else J_DIM
        label = "Failed" if is_error else "Done"
        line = Text()
        line.append("  ↳ ", style=color)
        line.append(f"{label}  ", style=f"bold {color}")
        line.append(_short(result, limit=140), style=color)
    else:
        color = S_ERROR if is_error else S_DIM
        label = "FAULT" if is_error else "RETURN"
        line = Text()
        line.append("  ↳ ", style=color)
        line.append(f"{label}  ", style=f"bold {color}")
        line.append(_short(result, limit=140), style=color)
    console.print(line)


# ─── SYSTEM, COST, AND READOUTS ──────────────────────────────────────────────

def render_system_message(text: str, level: str = "info") -> None:
    if mode.is_jarvis():
        color = {"info": J_DIM, "warn": J_WARN, "error": J_ERROR}.get(level, J_DIM)
        glyph = "◇"
    else:
        color = {"info": S_DIM, "warn": S_WARN, "error": S_ERROR}.get(level, S_DIM)
        glyph = "⟡"
    console.print(Text(f"{glyph} {text}", style=color))


def render_cost_line(usage) -> None:
    if mode.is_jarvis():
        text = Text()
        text.append("◇ ", style=J_ACCENT)
        text.append("usage  ", style=f"bold {J_ACCENT}")
        text.append(usage.summary(), style=J_DIM)
    else:
        text = Text()
        text.append("⟡ ", style=S_DIM)
        text.append("USAGE  ", style=f"bold {S_DIM}")
        text.append(usage.summary(), style=S_DIM)
    console.print(text)


def render_permissions(checks) -> None:
    """Pretty-print a permissions readout from health.run_checks()."""
    primary = J_PRIMARY if mode.is_jarvis() else S_PRIMARY
    dim = J_DIM if mode.is_jarvis() else S_DIM
    console.print(Rule(style=dim))
    title = "Diagnostics" if mode.is_jarvis() else "PRE-FLIGHT DIAGNOSTICS"
    console.print(Text(title, style=f"bold {primary}"))
    for label, status, detail in checks:
        if status == "ok":
            icon, color = ("✓", primary)
        elif status == "warn":
            icon, color = ("!", J_WARN if mode.is_jarvis() else S_WARN)
        else:
            icon, color = ("✗", J_ERROR if mode.is_jarvis() else S_ERROR)
        line = Text()
        line.append(f"  {icon}  ", style=color)
        line.append(f"{label:<14}", style=color)
        line.append(detail, style=dim)
        console.print(line)
    console.print(Rule(style=dim))


def render_sessions(sessions) -> None:
    """Pretty-print a list from session.list_sessions()."""
    primary = J_PRIMARY if mode.is_jarvis() else S_PRIMARY
    dim = J_DIM if mode.is_jarvis() else S_DIM
    if not sessions:
        render_system_message("No saved sessions.")
        return
    console.print(Rule(style=dim))
    console.print(Text("Saved sessions", style=f"bold {primary}"))
    for sid, updated_at, msg_count in sessions:
        when = datetime.fromtimestamp(updated_at).strftime("%Y-%m-%d %H:%M")
        line = Text()
        line.append(f"  {sid}", style=primary)
        line.append(f"  {when}", style=dim)
        line.append(f"  ({msg_count} msgs)", style=dim)
        console.print(line)
    console.print(Rule(style=dim))


# ─── GOODBYE ─────────────────────────────────────────────────────────────────

def goodbye() -> None:
    console.print()
    if mode.is_jarvis():
        console.print(Rule(style=J_DIM))
        user = os.environ.get("SAMARITAN_USER_NAME", "sir")
        console.print(Text(f"▽ Powering down. Until next time, {user}.", style=J_PRIMARY))
        console.print(Rule(style=J_DIM))
    else:
        console.print(Rule(style=S_DIM))
        console.print(Text("▌ SAMARITAN ─ SESSION TERMINATED. STANDING DOWN.", style=S_PRIMARY))
        console.print(Rule(style=S_DIM))


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _short(value, limit: int = 60) -> str:
    s = str(value).replace("\n", " ⏎ ")
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


__all__ = [
    "boot_sequence",
    "classification_banner",
    "confirm_action",
    "console",
    "end_stream_block",
    "goodbye",
    "prompt_input",
    "render_cost_line",
    "render_permissions",
    "render_response",
    "render_sessions",
    "render_system_message",
    "render_thinking",
    "render_tool_call",
    "render_tool_result",
    "start_stream_block",
    "stream_text",
]
