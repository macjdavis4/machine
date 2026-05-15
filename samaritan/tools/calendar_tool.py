"""Apple Calendar read access via AppleScript."""

from __future__ import annotations

import shutil
import subprocess

from samaritan.tools._hud import hud_tool


@hud_tool(
    description="List Apple Calendar events scheduled within the next N days.",
    properties={
        "days": {
            "type": "integer",
            "description": "Number of days to look ahead (1-14).",
            "default": 1,
        }
    },
)
def upcoming_calendar_events(days: int = 1) -> str:
    days = max(1, min(int(days), 14))
    if not shutil.which("osascript"):
        return "osascript not available — this tool only works on macOS."

    script = f"""
    set output to ""
    set nowDate to current date
    set endDate to nowDate + ({days} * days)
    tell application "Calendar"
        repeat with theCal in calendars
            try
                set evts to (every event of theCal whose start date is greater than or equal to nowDate and start date is less than endDate)
                repeat with e in evts
                    set output to output & ((start date of e) as string) & " │ " & (title of theCal) & " │ " & (summary of e) & linefeed
                end repeat
            end try
        end repeat
    end tell
    return output
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Calendar query timed out."

    if result.returncode != 0:
        return f"Calendar error: {result.stderr.strip()}"

    out = result.stdout.strip()
    return out or f"No events scheduled in the next {days} day(s)."
