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

from samaritan import health, mode, session, ui
from samaritan.agent import Samaritan


HELP = """Commands:
  /help                Show this help
  /mode                Show current mode (jarvis | samaritan)
  /mode jarvis         Switch to Jarvis personality + Stark-HUD visuals
  /mode samaritan      Switch to Samaritan personality + surveillance HUD
  /sessions            List saved sessions
  /load <id>           Load a saved session by id
  /save                Force-save current session
  /new                 Start a fresh session
  /clear               Clear conversation history (keep session id)
  /history             Show message count for current session
  /cost                Show cumulative token usage and estimated cost
  /permissions         Re-run pre-flight diagnostics
  /quit, /exit         End the session"""


def _handle_mode(arg: str, agent: Samaritan) -> None:
    if not arg:
        ui.render_system_message(f"Current mode: {mode.current()}")
        return
    try:
        new_mode = mode.set_mode(arg)
    except ValueError as exc:
        ui.render_system_message(str(exc), level="error")
        return
    # Switching the persona changes the system prompt, which invalidates
    # the cached prefix. Wipe history so the new voice starts fresh.
    agent.messages = []
    agent.refresh_system()
    agent.session.mode = new_mode
    agent.session.save()
    ui.classification_banner()
    ui.render_system_message(
        f"Mode switched to {new_mode}. Conversation reset."
    )


def _handle_sessions(agent: Samaritan) -> None:
    ui.render_sessions(session.list_sessions(limit=20))


def _handle_load(arg: str, agent: Samaritan) -> Samaritan:
    if not arg:
        ui.render_system_message("Usage: /load <session_id>", level="warn")
        return agent
    loaded = session.Session.load(arg.strip())
    if loaded is None:
        ui.render_system_message(f"No such session: {arg}", level="error")
        return agent
    # Persist current session before swapping
    agent.session.save()
    new_agent = Samaritan(session=loaded)
    mode_changed = False
    if loaded.mode and loaded.mode != mode.current():
        try:
            mode.set_mode(loaded.mode)
            mode_changed = True
        except ValueError:
            pass
    new_agent.refresh_system()
    if mode_changed:
        ui.classification_banner()
    ui.render_system_message(
        f"Loaded session {loaded.id} ({len(loaded.messages)} msgs, mode={loaded.mode})."
    )
    return new_agent


def _handle_new(agent: Samaritan) -> Samaritan:
    agent.session.save()
    new_agent = Samaritan(session=session.Session(mode=mode.current()))
    ui.render_system_message(f"New session: {new_agent.session.id}")
    return new_agent


def main() -> int:
    # Pre-flight diagnostics. Hard-fail only on missing/invalid API key.
    checks = health.run_checks()
    ui.boot_sequence()
    ui.classification_banner()
    ui.render_permissions(checks)
    if health.has_blocking_failures(checks):
        ui.render_system_message(
            "Cannot start — fix the failing checks and try again.", level="error"
        )
        return 2

    # Autoload last session if SAMARITAN_AUTOLOAD=1
    sess: session.Session | None = None
    if os.environ.get("SAMARITAN_AUTOLOAD") == "1":
        last_id = session.latest_session_id()
        if last_id:
            sess = session.Session.load(last_id)
            if sess:
                ui.render_system_message(
                    f"Auto-loaded last session: {sess.id} ({len(sess.messages)} msgs)"
                )
    if sess is None:
        sess = session.Session(mode=mode.current())

    agent = Samaritan(session=sess)
    ui.render_system_message(
        f"Active mode: {mode.current()}. Session: {agent.session.id}. /help for commands."
    )

    while True:
        try:
            line = ui.prompt_input().strip()
        except KeyboardInterrupt:
            ui.goodbye()
            return 0

        if not line:
            continue

        if line in ("/quit", "/exit", "/q"):
            agent.session.save()
            ui.goodbye()
            return 0

        if line == "/help":
            ui.render_system_message(HELP)
            continue

        if line == "/clear":
            agent.messages = []
            agent.session.save()
            ui.render_system_message("Conversation history cleared.")
            continue

        if line == "/history":
            ui.render_system_message(
                f"Session {agent.session.id}: {len(agent.messages)} message(s)."
            )
            continue

        if line == "/cost":
            ui.render_cost_line(agent.session.usage)
            continue

        if line == "/save":
            agent.session.save()
            ui.render_system_message(f"Saved: {agent.session.path}")
            continue

        if line == "/sessions":
            _handle_sessions(agent)
            continue

        if line == "/permissions":
            ui.render_permissions(health.run_checks())
            continue

        if line.startswith("/load"):
            agent = _handle_load(line[len("/load"):].strip(), agent)
            continue

        if line == "/new":
            agent = _handle_new(agent)
            continue

        if line.startswith("/mode"):
            _handle_mode(line[len("/mode"):].strip(), agent)
            continue

        # agent.turn() handles its own checkpoint/rollback for KeyboardInterrupt
        # and unexpected errors, then persists. No further action needed here.
        agent.turn(line)


if __name__ == "__main__":
    sys.exit(main())
