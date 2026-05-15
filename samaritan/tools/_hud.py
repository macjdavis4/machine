"""Tool decorator that wires every tool through:

  1. Disabled-tool check (denylist)
  2. Operator confirmation gate (for destructive/outbound tools)
  3. HUD call/result rendering
  4. Output capping (bytes ceiling on the string returned to the model)
  5. Audit log entry

The decorator factory takes a JSON Schema description; the wrapped function
exposes its schema on `wrapper.schema` so the agent can pass it to the API.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable

from samaritan import audit, safety, ui


def hud_tool(*, description: str, properties: dict, required: list[str] | None = None):
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
        name = fn.__name__

        @functools.wraps(fn)
        def wrapper(**kwargs):
            # 1. Denylist
            if safety.is_disabled(name):
                msg = safety.render_disabled_response(name)
                ui.render_tool_call(name, kwargs)
                ui.render_tool_result(name, msg, is_error=True)
                audit.record(name, kwargs, msg, is_error=True)
                return msg

            # 2. Confirmation gate
            if safety.needs_confirmation(name):
                ui.render_tool_call(name, kwargs)
                if not ui.confirm_action(name, kwargs):
                    msg = safety.render_denied_response(name)
                    ui.render_tool_result(name, msg, is_error=True)
                    audit.record(name, kwargs, msg, is_error=True)
                    return msg
            else:
                ui.render_tool_call(name, kwargs)

            # 3. Execute, with timing for the audit log
            started = time.monotonic()
            try:
                result = fn(**kwargs)
                is_error = False
            except Exception as exc:  # noqa: BLE001 — surfaced to the model
                result = f"{type(exc).__name__}: {exc}"
                is_error = True

            # 4. Cap the result string before it goes back to the model
            capped, truncated = safety.cap_output(str(result))

            # 5. Render and audit
            ui.render_tool_result(name, capped, is_error=is_error)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            audit.record(
                name,
                kwargs,
                capped,
                is_error=is_error,
                elapsed_ms=elapsed_ms,
            )
            if truncated:
                ui.render_system_message(
                    f"  ↳ {name} output truncated to {safety.max_tool_output_bytes()} bytes",
                    level="warn",
                )
            return capped

        wrapper.schema = schema  # type: ignore[attr-defined]
        return wrapper

    return decorator
