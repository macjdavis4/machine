# SAMARITAN

A Jarvis-class personal intelligence with Samaritan-class observational
output. Speaks like Jarvis served Tony Stark; displays like the
surveillance HUD from *Person of Interest*. Built on Claude Opus 4.7 with
native macOS integrations.

## Capabilities

- **Read iMessages** — Queries `~/Library/Messages/chat.db` read-only.
  Recent messages, full-text search, list active conversations.
- **Apple Notes** — Create new notes, append to existing notes, list
  recent notes by title, read note bodies.
- **Apple Calendar** — Read upcoming events for the next N days.
- **System status** — Battery, disk, network/SSID, CPU/RAM, uptime.
- **Voice** — Text-to-speech via `say` with a configurable voice
  (default: Daniel, British male).
- **Persistent memory** — A small JSON store under `~/.samaritan/` that
  survives across sessions; the model decides what to remember.
- **Web search & fetch** — Anthropic-hosted server-side tools for current
  events and live page content.
- **Conversation context** — Full multi-turn history maintained per
  session. The system prompt is prompt-cached.

## Quickstart

```bash
cp .env.example .env
# Edit .env, set ANTHROPIC_API_KEY=sk-ant-...
./run.sh
```

The first run creates a virtualenv and installs dependencies.

## macOS Permissions

The first time the relevant tools fire, macOS will prompt for:

- **Full Disk Access** — your terminal app, for reading `chat.db`.
  System Settings → Privacy & Security → Full Disk Access.
- **Automation: Notes** — for AppleScript access to Apple Notes.
- **Automation: Calendar** — for AppleScript access to Apple Calendar.

Without these, the corresponding tools return an error string that the
model will report back.

## Configuration

Environment variables (set in `.env` or your shell):

| Var | Default | Purpose |
|-----|---------|---------|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key. |
| `SAMARITAN_USER_NAME` | `Sir` | How the assistant addresses you. |
| `SAMARITAN_VOICE` | `Daniel` | macOS `say` voice. Try `Karen`, `Moira`, `Oliver`. |

## REPL Commands

| Command | Effect |
|---------|--------|
| `/help` | Show in-app help. |
| `/clear` | Reset conversation history (keeps the system prompt). |
| `/history` | How many messages are in the current session. |
| `/quit`, `/exit` | Disengage. |

Anything else is sent to Samaritan.

## How it Works

`samaritan/agent.py` uses `client.beta.messages.tool_runner()` from the
Anthropic Python SDK. The runner handles the multi-turn agent loop: call
the API, execute any tool calls the model requests, feed results back,
repeat until the model is done. Tools are defined in `samaritan/tools/`
using the `@hud_tool` decorator, which wraps each function with HUD
logging and then registers it as a Claude tool via `@beta_tool`.

The model runs with **adaptive thinking** (`display: "summarized"`) and
**effort: high**. The system prompt sits behind a `cache_control` block
so repeated turns within a session reuse the cached prefix.

## Layout

```
samaritan/
├── __main__.py            REPL entry point
├── agent.py               Agent loop (Anthropic tool runner)
├── persona.py             System prompt (the Jarvis voice)
├── ui.py                  Samaritan-style cyan HUD rendering
├── memory.py              Persistent JSON memory store
└── tools/
    ├── _hud.py            hud_tool decorator
    ├── messages.py        Read iMessages from chat.db
    ├── notes.py           Apple Notes via AppleScript
    ├── calendar_tool.py   Apple Calendar via AppleScript
    ├── system_info.py     Battery, disk, network, CPU, uptime
    ├── voice.py           say-command TTS
    └── memory_tool.py     remember/recall/forget facts
```

## Caveats

- macOS-only for the iMessages, Notes, Calendar, and voice tools. The
  rest of the app runs anywhere — useful for testing the agent itself.
- iMessage access is read-only; sending messages is intentionally not
  exposed.
- The memory store is plain JSON. Don't store secrets in it.
