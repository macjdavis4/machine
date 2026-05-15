"""Create reminders in Apple Reminders via AppleScript."""

from __future__ import annotations

import shutil
import subprocess

from samaritan.tools._hud import hud_tool


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


@hud_tool(
    description=(
        "Create a new entry in Apple Reminders. Optionally set a due date. "
        "Requires operator confirmation."
    ),
    properties={
        "title": {
            "type": "string",
            "description": "Reminder title.",
        },
        "due_date": {
            "type": "string",
            "description": (
                "Optional due date in AppleScript-friendly form, e.g. "
                "'Friday at 3:00 PM' or 'December 15, 2026 at 9:00 AM'."
            ),
            "default": "",
        },
    },
    required=["title"],
)
def set_reminder(title: str, due_date: str = "") -> str:
    if not shutil.which("osascript"):
        return "osascript not available — this tool only works on macOS."
    if due_date:
        script = (
            'tell application "Reminders"\n'
            "  set theDate to date \"" + _escape(due_date) + "\"\n"
            f'  make new reminder with properties {{name:"{_escape(title)}", '
            "due date:theDate}\n"
            "end tell"
        )
    else:
        script = (
            'tell application "Reminders"\n'
            f'  make new reminder with properties {{name:"{_escape(title)}"}}\n'
            "end tell"
        )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Reminder creation timed out."
    if result.returncode != 0:
        return f"Reminder error: {result.stderr.strip()}"
    suffix = f" (due {due_date})" if due_date else ""
    return f"Reminder created: {title}{suffix}"
