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

from samaritan import ui
from samaritan.agent import Samaritan


HELP = """Commands:
  /help          Show this help
  /clear         Clear conversation history (system prompt persists)
  /history       Show how many turns are in this session
  /quit, /exit   End the session

Anything else is sent to Samaritan."""


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        ui.render_system_message(
            "ANTHROPIC_API_KEY not set. Add it to .env or export it.", level="error"
        )
        return 2

    ui.boot_sequence()
    ui.classification_banner()
    ui.render_system_message(
        "Awaiting input. Type /help for commands, /quit to disengage."
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

        try:
            agent.turn(line)
        except KeyboardInterrupt:
            ui.render_system_message("Turn interrupted.", level="warn")
            # Drop the trailing user turn so history stays consistent
            if agent.messages and agent.messages[-1]["role"] == "user":
                agent.messages.pop()
            continue


if __name__ == "__main__":
    sys.exit(main())
