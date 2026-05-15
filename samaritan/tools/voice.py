"""Text-to-speech via the macOS `say` command."""

from __future__ import annotations

import os
import shutil
import subprocess

from samaritan.tools._hud import hud_tool


@hud_tool(
    description=(
        "Speak text aloud through the macOS speech synthesizer. Uses the voice "
        "configured by the SAMARITAN_VOICE environment variable (default: Daniel, "
        "British male). Keep spoken text short — a sentence or two."
    ),
    properties={
        "text": {
            "type": "string",
            "description": "The text to vocalize. Keep under 300 characters.",
        }
    },
    required=["text"],
)
def speak(text: str) -> str:
    if not shutil.which("say"):
        return "Voice unavailable — `say` command not found (macOS-only)."
    text = text.strip()
    if not text:
        return "Nothing to speak."
    if len(text) > 300:
        text = text[:297] + "..."
    voice = os.environ.get("SAMARITAN_VOICE", "Daniel")
    try:
        subprocess.run(
            ["say", "-v", voice, text],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Voice synthesis timed out."
    return f"Spoke: {text}"
