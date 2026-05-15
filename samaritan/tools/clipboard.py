"""Clipboard read/write via pbcopy/pbpaste."""

from __future__ import annotations

import shutil
import subprocess

from samaritan.tools._hud import hud_tool


@hud_tool(
    description="Read the current contents of the macOS clipboard.",
    properties={},
)
def clipboard_read() -> str:
    if not shutil.which("pbpaste"):
        return "pbpaste not available — clipboard read is macOS-only."
    try:
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5, check=False
        )
    except subprocess.TimeoutExpired:
        return "Clipboard read timed out."
    return result.stdout or "(clipboard is empty)"


@hud_tool(
    description="Replace the macOS clipboard contents with the given text.",
    properties={
        "text": {
            "type": "string",
            "description": "Text to write to the clipboard. Replaces existing content.",
        }
    },
    required=["text"],
)
def clipboard_write(text: str) -> str:
    if not shutil.which("pbcopy"):
        return "pbcopy not available — clipboard write is macOS-only."
    try:
        subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Clipboard write timed out."
    return f"Copied {len(text)} character(s) to clipboard."
