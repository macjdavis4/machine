"""The Samaritan agent loop — streaming, compacted, persistent.

Each user turn drives a streaming agentic loop against Claude Opus 4.7:

  1. Open a stream via `client.beta.messages.stream(...)` so thinking and
     text deltas arrive incrementally and `max_tokens` can reach 64K+
     without hitting the SDK's non-streaming HTTP-timeout guard.
  2. Render thinking and text deltas live as they arrive.
  3. After the stream ends, collect the final message, execute any
     tool_use blocks via TOOL_MAP, push tool_result blocks, loop.
  4. Stop when stop_reason == "end_turn", refusal, or we hit MAX_TOOL_ROUNDS.

Reliability:
  - The SDK auto-retries 429s and 5xx errors with exponential backoff
    (configured via `max_retries=5`).
  - APIStatusError and APIConnectionError are caught at the API call
    site; the failed user turn is rolled back so the next attempt starts
    with consistent state.
  - Beta header `compact-2026-01-12` plus `context_management` lets long
    sessions exceed the context window via server-side summarization.
    Compaction blocks in the response are preserved by appending the
    full `response.content` back to history.
  - Per-turn `usage` is accumulated into a session-wide `Usage` object
    and the session is auto-saved after every turn.
"""

from __future__ import annotations

from typing import Any

import anthropic

from samaritan import ui
from samaritan.persona import current_prompt
from samaritan.session import Session
from samaritan.tools import TOOL_MAP, TOOL_SCHEMAS

# Server-hosted tools the model can invoke; Anthropic executes these.
SERVER_TOOLS: list[dict[str, Any]] = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]

BETAS = ["compact-2026-01-12"]


class Samaritan:
    """Stateful streaming chat session against Claude Opus 4.7."""

    MODEL = "claude-opus-4-7"
    MAX_TOKENS = 32000  # Streamed, so SDK HTTP timeout is not a concern
    MAX_TOOL_ROUNDS = 16  # Per-user-turn cap on tool-use cycles

    def __init__(self, session: Session | None = None) -> None:
        # The SDK retries 429 and 5xx errors with exponential backoff.
        # `max_retries=5` gives roughly 30s of total backoff on persistent
        # rate limits before we surface the error.
        self.client = anthropic.Anthropic(max_retries=5, timeout=120.0)
        self.system = current_prompt()
        self.session = session or Session()

    # ─── Public API ─────────────────────────────────────────────────────────

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self.session.messages

    @messages.setter
    def messages(self, value: list[dict[str, Any]]) -> None:
        self.session.messages = value

    def refresh_system(self) -> None:
        """Re-resolve the system prompt — call after a mode switch."""
        self.system = current_prompt()

    def turn(self, user_input: str) -> None:
        """Process one user turn end-to-end."""
        self.messages.append({"role": "user", "content": user_input})

        try:
            self._loop()
        finally:
            # Always persist — even on abort/error — so the conversation
            # state on disk matches what's in memory.
            self.session.save()

    # ─── Internals ──────────────────────────────────────────────────────────

    def _loop(self) -> None:
        for round_idx in range(self.MAX_TOOL_ROUNDS):
            response = self._stream_one_response()
            if response is None:
                # API failure — rollback the user turn so retry is clean.
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                return

            self.session.usage.add(response.usage)
            self.messages.append({"role": "assistant", "content": response.content})

            stop = response.stop_reason
            if stop == "end_turn":
                ui.render_cost_line(self.session.usage)
                return
            if stop == "refusal":
                ui.render_system_message(
                    "Model declined the request.", level="warn"
                )
                ui.render_cost_line(self.session.usage)
                return
            if stop == "pause_turn":
                # Server-side tool hit its iteration limit. Re-send to resume.
                continue
            if stop == "tool_use":
                tool_results = self._execute_tool_uses(response)
                if tool_results:
                    self.messages.append({"role": "user", "content": tool_results})
                continue
            if stop == "max_tokens":
                ui.render_system_message(
                    f"Hit max_tokens={self.MAX_TOKENS}. Response truncated.",
                    level="warn",
                )
                ui.render_cost_line(self.session.usage)
                return

            ui.render_system_message(
                f"Unexpected stop_reason: {stop}", level="warn"
            )
            ui.render_cost_line(self.session.usage)
            return

        ui.render_system_message(
            f"Hit tool-round cap ({self.MAX_TOOL_ROUNDS}). Standing down.",
            level="warn",
        )
        ui.render_cost_line(self.session.usage)

    def _stream_one_response(self):
        """Stream one API call and return the final message, or None on failure."""
        try:
            with self.client.beta.messages.stream(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                betas=BETAS,
                system=[
                    {
                        "type": "text",
                        "text": self.system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                thinking={"type": "adaptive", "display": "summarized"},
                output_config={"effort": "high"},
                context_management={
                    "edits": [{"type": "compact_20260112"}],
                },
                tools=TOOL_SCHEMAS + SERVER_TOOLS,
                messages=self.messages,
            ) as stream:
                self._render_stream(stream)
                return stream.get_final_message()
        except anthropic.AuthenticationError:
            ui.render_system_message(
                "Anthropic auth failed. Check ANTHROPIC_API_KEY.", level="error"
            )
        except anthropic.RateLimitError as exc:
            ui.render_system_message(
                f"Rate limited after retries: {exc.message}", level="error"
            )
        except anthropic.APIStatusError as exc:
            ui.render_system_message(
                f"API error ({exc.status_code}): {exc.message}", level="error"
            )
        except anthropic.APIConnectionError as exc:
            ui.render_system_message(f"Connection error: {exc}", level="error")
        except KeyboardInterrupt:
            ui.render_system_message("Stream interrupted.", level="warn")
        return None

    def _render_stream(self, stream) -> None:
        """Render thinking + text deltas live as they arrive."""
        current_block: str | None = None
        for event in stream:
            etype = getattr(event, "type", None)
            if etype == "content_block_start":
                block = getattr(event, "content_block", None)
                btype = getattr(block, "type", None)
                if btype == "thinking":
                    ui.start_stream_block("thinking")
                    current_block = "thinking"
                elif btype == "text":
                    ui.start_stream_block("text")
                    current_block = "text"
                elif btype == "server_tool_use":
                    ui.render_tool_call(
                        getattr(block, "name", "server_tool"),
                        getattr(block, "input", {}) or {},
                    )
                # tool_use blocks: silent here; they execute after the stream.
            elif etype == "content_block_delta":
                delta = getattr(event, "delta", None)
                dtype = getattr(delta, "type", None)
                if dtype == "thinking_delta" and current_block == "thinking":
                    ui.stream_text(getattr(delta, "thinking", ""), kind="thinking")
                elif dtype == "text_delta" and current_block == "text":
                    ui.stream_text(getattr(delta, "text", ""), kind="text")
            elif etype == "content_block_stop":
                if current_block:
                    ui.end_stream_block(current_block)
                    current_block = None

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
            output = tool(**(block.input or {}))
            # tool() rendered + audited + capped via the hud_tool wrapper.
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output),
                }
            )
        return results
