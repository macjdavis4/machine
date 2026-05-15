"""Apple Notes integration via AppleScript."""

from __future__ import annotations

import re
import shutil
import subprocess

from samaritan.tools._hud import hud_tool


def _osascript(script: str) -> str:
    if not shutil.which("osascript"):
        return "osascript not available — this tool only works on macOS."
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Notes operation timed out."
    if result.returncode != 0:
        err = result.stderr.strip() or "unknown error"
        return f"Notes error: {err}"
    return result.stdout.strip()


def _escape(s: str) -> str:
    """Escape a string for embedding in an AppleScript double-quoted literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


@hud_tool(
    description="Create a new note in Apple Notes with the given title and body.",
    properties={
        "title": {"type": "string", "description": "The note's title (first line)."},
        "body": {
            "type": "string",
            "description": "The note's body content. Can include line breaks.",
            "default": "",
        },
    },
    required=["title"],
)
def create_apple_note(title: str, body: str = "") -> str:
    full = title if not body else f"{title}\n\n{body}"
    script = (
        'tell application "Notes"\n'
        f'  set newNote to make new note with properties {{body:"{_escape(full)}"}}\n'
        "  return id of newNote\n"
        "end tell"
    )
    out = _osascript(script)
    if out.startswith("Notes error") or out.startswith("osascript"):
        return out
    return f"Note created: {title}"


@hud_tool(
    description="Append text to the first existing note whose title contains the given string.",
    properties={
        "title": {
            "type": "string",
            "description": "Substring of the target note's title (case-sensitive).",
        },
        "text": {
            "type": "string",
            "description": "Text to append to the note's body.",
        },
    },
    required=["title", "text"],
)
def append_to_apple_note(title: str, text: str) -> str:
    script = (
        'tell application "Notes"\n'
        f'  set candidates to notes whose name contains "{_escape(title)}"\n'
        '  if (count of candidates) = 0 then return "NOT_FOUND"\n'
        "  set target to item 1 of candidates\n"
        f'  set body of target to (body of target) & "<br>" & "{_escape(text)}"\n'
        "  return name of target\n"
        "end tell"
    )
    out = _osascript(script)
    if out == "NOT_FOUND":
        return f"No note found with title containing '{title}'."
    if out.startswith("Notes error") or out.startswith("osascript"):
        return out
    return f"Appended to note: {out}"


@hud_tool(
    description="List recent Apple Notes by title.",
    properties={
        "limit": {
            "type": "integer",
            "description": "Maximum number of note titles to return (1-100).",
            "default": 20,
        }
    },
)
def list_apple_notes(limit: int = 20) -> str:
    limit = max(1, min(int(limit), 100))
    script = (
        'tell application "Notes"\n'
        "  set output to {}\n"
        "  set allNotes to notes\n"
        "  set n to (count of allNotes)\n"
        f"  if n > {limit} then set n to {limit}\n"
        "  repeat with i from 1 to n\n"
        '    set end of output to (name of item i of allNotes) & "\n"\n'
        "  end repeat\n"
        '  set AppleScript\'s text item delimiters to ""\n'
        "  return output as string\n"
        "end tell"
    )
    out = _osascript(script)
    if out.startswith("Notes error") or out.startswith("osascript"):
        return out
    return out.strip() or "No notes found."


@hud_tool(
    description="Read the full body of the first note whose title contains the given string.",
    properties={
        "title": {
            "type": "string",
            "description": "Substring of the note's title (case-sensitive).",
        }
    },
    required=["title"],
)
def read_apple_note(title: str) -> str:
    script = (
        'tell application "Notes"\n'
        f'  set candidates to notes whose name contains "{_escape(title)}"\n'
        '  if (count of candidates) = 0 then return "NOT_FOUND"\n'
        "  return body of item 1 of candidates\n"
        "end tell"
    )
    out = _osascript(script)
    if out == "NOT_FOUND":
        return f"No note found with title containing '{title}'."
    if out.startswith("Notes error") or out.startswith("osascript"):
        return out
    # Notes returns HTML — strip common tags so the model gets plain text.
    text = re.sub(r"<br\s*/?>", "\n", out)
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return text.strip()
