"""Open a URL or file path in the default macOS handler."""

from __future__ import annotations

import shutil
import subprocess
from urllib.parse import urlparse

from samaritan.tools._hud import hud_tool

_ALLOWED_SCHEMES = {"http", "https", "mailto", "tel", "facetime"}


@hud_tool(
    description=(
        "Open a URL (http/https/mailto/tel/facetime) in the default macOS handler. "
        "Requires operator confirmation."
    ),
    properties={
        "url": {
            "type": "string",
            "description": "Fully-qualified URL to open.",
        }
    },
    required=["url"],
)
def open_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return (
            f"Refusing: scheme '{parsed.scheme}' not allowed. "
            f"Allowed: {', '.join(sorted(_ALLOWED_SCHEMES))}."
        )
    if not shutil.which("open"):
        return "`open` not available — this tool only works on macOS."
    try:
        subprocess.run(
            ["open", url], capture_output=True, text=True, timeout=5, check=False
        )
    except subprocess.TimeoutExpired:
        return "Open command timed out."
    return f"Opened: {url}"
