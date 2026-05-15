"""Samaritan REPL.

Run with: python -m samaritan
"""

from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from samaritan import mode, ui
from samaritan.agent import Samaritan


HELP = """Commands:
  /help                Show this help
  /mode                Show current mode (jarvis | samaritan)
  /mode jarvis         Switch to Jarvis personality + Stark-HUD visuals
  /mode samaritan      Switch to Samaritan personality + surveillance HUD
  /clear               Clear conversation history (system prompt persists)
  /history             Show how many turns are in this session
  /quit, /exit         End the session

Anything else is sent to the assistant."""


def _handle_mode_command(arg: str, agent: Samaritan) -> None:
    if not arg:
        ui.render_system_message(f"Current mode: {mode.current()}")
        return
    try:
        new_mode = mode.set_mode(arg)
    except ValueError as exc:
        ui.render_system_message(str(exc), level="error")
        return
    # Switching the persona changes the system prompt, which invalidates the
    # conversation's cached prefix. Wipe history so the next turn starts fresh
    # in the new voice rather than mid-conversation in someone else's.
    agent.messages = []
    agent.refresh_system()
    ui.classification_banner()
    ui.render_system_message(
        f"Mode switched to {new_mode}. Conversation reset."
    )


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        ui.render_system_message(
            "ANTHROPIC_API_KEY not set. Add it to .env or export it.", level="error"
        )
        return 2

    ui.boot_sequence()
    ui.classification_banner()
    ui.render_system_message(
        f"Active mode: {mode.current()}. /help for commands, /mode to switch, /quit to disengage."
    )

    agent = Samaritan()

    while True:
        try:
            line = ui.prompt_input().strip()
        except KeyboardInterrupt:
            ui.goodbye()
            return 0

        if not line:
            continue

        if line in ("/quit", "/exit", "/q"):
            ui.goodbye()
            return 0

        if line == "/help":
            ui.render_system_message(HELP)
            continue

        if line == "/clear":
            agent.messages = []
            ui.render_system_message("Conversation history cleared.")
            continue

        if line == "/history":
            ui.render_system_message(
                f"{len(agent.messages)} message(s) in current session."
            )
            continue

        if line.startswith("/mode"):
            arg = line[len("/mode"):].strip()
            _handle_mode_command(arg, agent)
            continue

        try:
            agent.turn(line)
        except KeyboardInterrupt:
            ui.render_system_message("Turn interrupted.", level="warn")
            if agent.messages and agent.messages[-1]["role"] == "user":
                agent.messages.pop()
            continue


if __name__ == "__main__":
    sys.exit(main())
