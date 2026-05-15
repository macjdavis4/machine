"""Persistent memory exposed as tools to the model."""

from samaritan import memory
from samaritan.tools._hud import hud_tool


@hud_tool(
    description=(
        "Store a durable fact about the operator across sessions. Use for stable "
        "info: operator's name, recurring contacts, project names, preferences. "
        "Avoid ephemeral context."
    ),
    properties={
        "key": {
            "type": "string",
            "description": "Short identifier for the fact (e.g. 'operator_name', 'wife_name').",
        },
        "value": {"type": "string", "description": "The fact itself."},
    },
    required=["key", "value"],
)
def remember_fact(key: str, value: str) -> str:
    return memory.remember(key, value)


@hud_tool(
    description="Recall stored facts about the operator. With no key, returns all facts.",
    properties={
        "key": {
            "type": "string",
            "description": "Optional specific fact key. Leave empty for all facts.",
            "default": "",
        }
    },
)
def recall_facts(key: str = "") -> str:
    return memory.recall(key or None)


@hud_tool(
    description="Remove a stored fact from persistent memory.",
    properties={"key": {"type": "string", "description": "The fact key to delete."}},
    required=["key"],
)
def forget_fact(key: str) -> str:
    return memory.forget(key)
