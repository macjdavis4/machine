"""Tool registry.

Each tool module decorates its function with `@hud_tool(...)`, which attaches a
`.schema` dict (the JSON Schema sent to the API) and wraps the call with HUD
logging. The agent uses `TOOL_SCHEMAS` for the API request and `TOOL_MAP` to
dispatch tool_use blocks back to the matching callable.
"""

from samaritan.tools._hud import hud_tool
from samaritan.tools.calendar_tool import upcoming_calendar_events
from samaritan.tools.memory_tool import forget_fact, recall_facts, remember_fact
from samaritan.tools.messages import (
    list_recent_message_threads,
    read_imessages,
    search_imessages,
)
from samaritan.tools.notes import (
    append_to_apple_note,
    create_apple_note,
    list_apple_notes,
    read_apple_note,
)
from samaritan.tools.system_info import system_status
from samaritan.tools.voice import speak

ALL_TOOLS = [
    # Communications — iMessages (read-only)
    list_recent_message_threads,
    read_imessages,
    search_imessages,
    # Notes
    list_apple_notes,
    create_apple_note,
    append_to_apple_note,
    read_apple_note,
    # Calendar
    upcoming_calendar_events,
    # System
    system_status,
    # Voice
    speak,
    # Memory
    remember_fact,
    recall_facts,
    forget_fact,
]

TOOL_SCHEMAS = [t.schema for t in ALL_TOOLS]
TOOL_MAP = {t.schema["name"]: t for t in ALL_TOOLS}

__all__ = ["ALL_TOOLS", "TOOL_SCHEMAS", "TOOL_MAP", "hud_tool"]
