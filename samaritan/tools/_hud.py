"""Tool decorator and registry.

`@hud_tool(schema)` wraps a function with:
  1. UI logging (renders SUBROUTINE/RETURN lines to the Samaritan HUD).
  2. A `.schema` attribute carrying the JSON schema for the model.
  3. The function's `name` from `__name__` (overridable in the schema dict).

The agent collects all such tools, hands their schemas to the API, and dispatches
tool_use blocks to the matching function via a name→callable map.
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from samaritan import ui


def hud_tool(*, description: str, properties: dict, required: list[str] | None = None):
    """Decorator factory that returns a configured @hud_tool decorator.

    Args:
        description: Tool description shown to the model.
        properties: JSON Schema `properties` block for the tool's inputs.
        required: List of required property names. Defaults to empty.
    """
    required_list = list(required) if required else []

    def decorator(fn: Callable) -> Callable:
        schema: dict[str, Any] = {
            "name": fn.__name__,
            "description": description.strip(),
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required_list,
            },
        }

        @functools.wraps(fn)
        def wrapper(**kwargs):
            ui.render_tool_call(fn.__name__, kwargs)
            try:
                result = fn(**kwargs)
            except Exception as exc:  # noqa: BLE001 — surfaced to the model
                err = f"{type(exc).__name__}: {exc}"
                ui.render_tool_result(fn.__name__, err, is_error=True)
                return err
            ui.render_tool_result(fn.__name__, result)
            return result

        wrapper.schema = schema  # type: ignore[attr-defined]
        return wrapper

    return decorator
