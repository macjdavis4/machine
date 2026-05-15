"""Read iMessages from the macOS Messages SQLite database.

Requires Full Disk Access for the terminal/Python process; macOS will prompt
the first time. The database is opened read-only.

Apple stores message dates as nanoseconds since 2001-01-01 UTC (Cocoa epoch).
We convert to local-timezone ISO format on the way out.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from samaritan.tools._hud import hud_tool

_CHAT_DB = Path(os.path.expanduser("~/Library/Messages/chat.db"))
_COCOA_EPOCH_OFFSET = 978307200  # seconds between 1970-01-01 and 2001-01-01


def _cocoa_ns_to_iso(ns: int) -> str:
    if not ns:
        return ""
    seconds = ns / 1_000_000_000 + _COCOA_EPOCH_OFFSET
    return (
        datetime.fromtimestamp(seconds, tz=timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds")
    )


@contextmanager
def _open_db():
    if not _CHAT_DB.exists():
        raise FileNotFoundError(
            f"Messages database not found at {_CHAT_DB}. This tool only works on macOS."
        )
    uri = f"file:{_CHAT_DB}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _format_rows(rows) -> str:
    out = []
    for r in rows:
        ts = _cocoa_ns_to_iso(r["date"])
        sender = "me" if r["is_from_me"] else (r["handle"] or "unknown")
        body = (r["text"] or "").replace("\n", " ").strip() or "[non-text content]"
        out.append(f"[{ts}] {sender}: {body}")
    return "\n".join(out) if out else "No messages found."


@hud_tool(
    description="Read the most recent iMessages across all conversations.",
    properties={
        "limit": {
            "type": "integer",
            "description": "Maximum number of messages to return (1-200).",
            "default": 20,
        }
    },
)
def read_imessages(limit: int = 20) -> str:
    limit = max(1, min(int(limit), 200))
    try:
        with _open_db() as conn:
            rows = conn.execute(
                """
                SELECT m.date, m.text, m.is_from_me, h.id AS handle
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                ORDER BY m.date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return _format_rows(reversed(rows))
    except FileNotFoundError as e:
        return str(e)
    except sqlite3.OperationalError as e:
        return (
            f"Could not read Messages database: {e}. "
            "Grant Full Disk Access to your terminal in System Settings → Privacy & Security."
        )


@hud_tool(
    description="Search iMessages by substring (case-insensitive) in message text or contact handle.",
    properties={
        "query": {
            "type": "string",
            "description": "Substring to find in message text or contact handle (phone/email).",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of matching messages to return (1-200).",
            "default": 20,
        },
    },
    required=["query"],
)
def search_imessages(query: str, limit: int = 20) -> str:
    limit = max(1, min(int(limit), 200))
    needle = f"%{query}%"
    try:
        with _open_db() as conn:
            rows = conn.execute(
                """
                SELECT m.date, m.text, m.is_from_me, h.id AS handle
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.text LIKE ? COLLATE NOCASE
                   OR h.id   LIKE ? COLLATE NOCASE
                ORDER BY m.date DESC
                LIMIT ?
                """,
                (needle, needle, limit),
            ).fetchall()
        return _format_rows(reversed(rows))
    except FileNotFoundError as e:
        return str(e)
    except sqlite3.OperationalError as e:
        return f"Could not read Messages database: {e}"


@hud_tool(
    description="List the most recently active iMessage conversations (group chats and DMs).",
    properties={
        "limit": {
            "type": "integer",
            "description": "Maximum number of threads to return (1-50).",
            "default": 10,
        }
    },
)
def list_recent_message_threads(limit: int = 10) -> str:
    limit = max(1, min(int(limit), 50))
    try:
        with _open_db() as conn:
            rows = conn.execute(
                """
                SELECT c.display_name, c.chat_identifier,
                       MAX(m.date) AS last_date,
                       COUNT(m.ROWID) AS msg_count
                FROM chat c
                JOIN chat_message_join cmj ON cmj.chat_id = c.ROWID
                JOIN message m ON m.ROWID = cmj.message_id
                GROUP BY c.ROWID
                ORDER BY last_date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        if not rows:
            return "No conversations found."
        lines = []
        for r in rows:
            label = r["display_name"] or r["chat_identifier"] or "unknown"
            lines.append(
                f"[{_cocoa_ns_to_iso(r['last_date'])}] {label}  ({r['msg_count']} msgs)"
            )
        return "\n".join(lines)
    except FileNotFoundError as e:
        return str(e)
    except sqlite3.OperationalError as e:
        return f"Could not read Messages database: {e}"
