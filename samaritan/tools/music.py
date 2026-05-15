"""Control Apple Music via AppleScript."""

from __future__ import annotations

import shutil
import subprocess

from samaritan.tools._hud import hud_tool

_COMMANDS = {
    "play": 'tell application "Music" to play',
    "pause": 'tell application "Music" to pause',
    "next": 'tell application "Music" to next track',
    "previous": 'tell application "Music" to previous track',
    "status": (
        'tell application "Music"\n'
        "  if player state is playing then\n"
        "    set t to (name of current track) & \" — \" & (artist of current track)\n"
        "    return \"playing: \" & t\n"
        "  else\n"
        "    return \"paused\"\n"
        "  end if\n"
        "end tell"
    ),
}


@hud_tool(
    description=(
        "Control Apple Music: play, pause, next, previous, or status. "
        "Requires operator confirmation."
    ),
    properties={
        "action": {
            "type": "string",
            "enum": list(_COMMANDS.keys()),
            "description": "Which action to perform.",
        }
    },
    required=["action"],
)
def music_control(action: str) -> str:
    if action not in _COMMANDS:
        return f"Unknown action '{action}'. Choose: {', '.join(_COMMANDS.keys())}."
    if not shutil.which("osascript"):
        return "osascript not available — this tool only works on macOS."
    try:
        result = subprocess.run(
            ["osascript", "-e", _COMMANDS[action]],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Music command timed out."
    if result.returncode != 0:
        return f"Music error: {result.stderr.strip()}"
    return result.stdout.strip() or f"Music: {action}"
