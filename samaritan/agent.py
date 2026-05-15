"""The Samaritan agent loop.

Manual agentic loop against Claude Opus 4.7 with adaptive thinking, effort=high,
and prompt-cached system prompt. Per iteration: call the API, render thinking
and text blocks, execute any tool_use blocks via TOOL_MAP, feed results back,
continue until stop_reason == "end_turn".

Server-side tools (web_search, web_fetch) live alongside our local tools and
execute on Anthropic's infrastructure — we just declare them and render the
result blocks that come back.
"""

from __future__ import annotations

from typing import Any

import anthropic

from samaritan import ui
from samaritan.persona import system_prompt
from samaritan.tools import TOOL_MAP, TOOL_SCHEMAS

# Server-hosted tools the model can invoke; Anthropic executes these.
SERVER_TOOLS: list[dict[str, Any]] = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]


class Samaritan:
    """Stateful chat session against Claude Opus 4.7."""

    MODEL = "claude-opus-4-7"
    MAX_TOKENS = 16000  # Safe under SDK HTTP timeout for non-streaming
    MAX_TOOL_ROUNDS = 12  # Per-user-turn cap on tool-use cycles

    def __init__(self) -> None:
        self.client = anthropic.Anthropic()
        self.system = system_prompt()
        self.messages: list[dict[str, Any]] = []

    def refresh_system(self) -> None:
        """Re-resolve the system prompt — call after a mode switch."""
        self.system = system_prompt()

    def turn(self, user_input: str) -> None:
        """Process one user turn end-to-end."""
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.MAX_TOOL_ROUNDS):
            try:
                response = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=self.MAX_TOKENS,
                    system=[
                        {
                            "type": "text",
                            "text": self.system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    thinking={"type": "adaptive", "display": "summarized"},
                    output_config={"effort": "high"},
                    tools=TOOL_SCHEMAS + SERVER_TOOLS,
                    messages=self.messages,
                )
            except anthropic.APIStatusError as exc:
                ui.render_system_message(
                    f"API error ({exc.status_code}): {exc.message}", level="error"
                )
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                return
            except anthropic.APIConnectionError as exc:
                ui.render_system_message(f"Connection error: {exc}", level="error")
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                return

            self._render(response)
            # Always preserve the full content (including thinking blocks) — required
            # by the API for any subsequent turn that includes a tool_result.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return
            if response.stop_reason == "refusal":
                ui.render_system_message(
                    "Model declined the request.", level="warn"
                )
                return
            if response.stop_reason == "pause_turn":
                # Server-side tool hit its iteration limit; re-send to resume.
                continue
            if response.stop_reason == "tool_use":
                tool_results = self._execute_tool_uses(response)
                if tool_results:
                    self.messages.append({"role": "user", "content": tool_results})
                continue
            # Unknown stop reason — surface and bail.
            ui.render_system_message(
                f"Unexpected stop_reason: {response.stop_reason}", level="warn"
            )
            return

        ui.render_system_message(
            f"Hit tool-round cap ({self.MAX_TOOL_ROUNDS}). Standing down.",
            level="warn",
        )

    def _render(self, response) -> None:
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "thinking":
                ui.render_thinking(getattr(block, "thinking", ""))
            elif btype == "text":
                ui.render_response(getattr(block, "text", ""))
            elif btype == "server_tool_use":
                ui.render_tool_call(
                    getattr(block, "name", "server_tool"),
                    getattr(block, "input", {}) or {},
                )
            elif btype and btype.endswith("_tool_result"):
                summary = _summarize_server_result(block)
                if summary:
                    ui.render_tool_result(btype, summary)
            # tool_use blocks render themselves when dispatched below.

    def _execute_tool_uses(self, response) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            name = block.name
            tool = TOOL_MAP.get(name)
            if tool is None:
                err = f"Unknown tool: {name}"
                ui.render_tool_result(name, err, is_error=True)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": err,
                        "is_error": True,
                    }
                )
                continue
            try:
                output = tool(**(block.input or {}))
                # tool() already rendered call/result via hud_tool wrapper.
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    }
                )
            except Exception as exc:  # noqa: BLE001 — surfaced to the model
                err = f"{type(exc).__name__}: {exc}"
                ui.render_tool_result(name, err, is_error=True)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": err,
                        "is_error": True,
                    }
                )
        return results


def _summarize_server_result(block) -> str:
    content = getattr(block, "content", None)
    if content is None:
        return ""
    if isinstance(content, list):
        return f"{len(content)} item(s) returned"
    return str(content)[:140]
