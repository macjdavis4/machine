# SAMARITAN / JARVIS

A personal intelligence with two faces. Switch at any time between:

- **`jarvis`** — Stark-Industries holographic blue HUD, warm British
  butler voice, anticipatory and dryly witty.
- **`samaritan`** — Surveillance-grade cyan classification HUD, cold
  observational voice, briefings rather than conversation.

Same model, same tools, two completely different personalities and visual
languages. Built on Claude Opus 4.7 with native macOS integrations.

## Capabilities

| Tool | Read / Write | Confirm? |
|------|---|---|
| `read_imessages`, `search_imessages`, `list_recent_message_threads` | R | — |
| `list_apple_notes`, `read_apple_note` | R | — |
| `create_apple_note`, `append_to_apple_note` | W | ✓ |
| `upcoming_calendar_events` | R | — |
| `set_reminder` | W | ✓ |
| `system_status` | R | — |
| `clipboard_read` | R | — |
| `clipboard_write` | W | ✓ |
| `open_url` | W | ✓ |
| `music_control` | W | ✓ |
| `speak` | W | ✓ |
| `remember_fact`, `recall_facts` | R/W | — |
| `forget_fact` | W | ✓ |
| `web_search`, `web_fetch` (Anthropic-hosted) | R | — |

Plus per-session conversation state, prompt caching, and **server-side
compaction** for long conversations (Beta `compact-2026-01-12`).

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
- **Automation: Notes / Calendar / Reminders / Music** — AppleScript access.

Without these, the corresponding tools return an error string. Use
`/permissions` inside the REPL to re-run diagnostics at any time.

## Configuration

| Env var | Default | Purpose |
|--------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Required. |
| `SAMARITAN_MODE` | `samaritan` | Startup mode: `jarvis` or `samaritan`. |
| `SAMARITAN_USER_NAME` | `Sir` | How the assistant addresses you. |
| `SAMARITAN_VOICE` | `Daniel` | macOS `say` voice. |
| `SAMARITAN_AUTOLOAD` | `0` | `1` to auto-resume the most recent session. |
| `SAMARITAN_AUTO_APPROVE` | `0` | `1` to skip confirmation prompts (dangerous). |
| `SAMARITAN_DISABLE_TOOLS` | (empty) | Comma-separated tool names to refuse. |
| `SAMARITAN_MAX_TOOL_OUTPUT` | `8192` | Bytes returned to the model per tool call. |

## REPL Commands

| Command | Effect |
|---------|--------|
| `/help` | Show in-app help. |
| `/mode [jarvis\|samaritan]` | Show or switch persona + UI mode. |
| `/sessions` | List saved sessions. |
| `/load <id>` | Resume a saved session. |
| `/save` | Force-save the current session. |
| `/new` | Start a fresh session. |
| `/clear` | Wipe conversation history (keep session id). |
| `/history` | Show message count for current session. |
| `/cost` | Show cumulative token usage and estimated cost. |
| `/permissions` | Re-run pre-flight diagnostics. |
| `/quit`, `/exit` | Disengage. |

Switching `/mode` resets the conversation so the new voice starts fresh
rather than mid-thought as someone else.

## Reliability

- **Streaming** — every API call uses `client.beta.messages.stream()`,
  so thinking and text appear incrementally and `max_tokens` can reach
  32K+ without HTTP-timeout risk.
- **Auto-retry** — the Anthropic SDK retries 429 / 5xx errors with
  exponential backoff (`max_retries=5`).
- **Compaction** — long sessions are summarized server-side via the
  `compact-2026-01-12` beta and `context_management.edits`.
- **Auto-save** — every turn writes the session to
  `~/.samaritan/sessions/<id>.json` (atomic via temp-file + rename).
- **Failed turn rollback** — if an API call fails, the user turn is
  popped from history so retry starts clean.
- **Audit log** — every tool call is recorded to `~/.samaritan/audit.log`
  (JSONL; rotated at 5 MB). Result bodies are hashed, not stored.
- **Output capping** — tool returns over 8 KB (configurable) are
  truncated before going back to the model so a runaway query doesn't
  blow up context.
- **Memory bounds** — the fact store caps at 200 entries, 8 KB / value,
  64 chars / key.

## Layout

```
samaritan/
├── __main__.py            REPL entry point + slash commands
├── agent.py               Streaming agent loop with compaction + retry
├── persona.py             Both system prompts (Jarvis + Samaritan)
├── ui.py                  Both HUDs + streaming primitives
├── mode.py                Runtime mode switch + persistence
├── session.py             Conversation save/load to ~/.samaritan/sessions/
├── safety.py              Denylist, confirmation gates, output capping
├── audit.py               JSONL audit log
├── cost.py                Token + USD accounting
├── health.py              Startup diagnostics (API, chat.db, osascript, …)
├── memory.py              Bounded persistent fact store
└── tools/
    ├── _hud.py            Decorator: denylist → confirm → run → cap → audit
    ├── messages.py        Read iMessages (read-only)
    ├── notes.py           Apple Notes (read + write)
    ├── calendar_tool.py   Apple Calendar (read)
    ├── reminders.py       Apple Reminders (write)
    ├── music.py           Apple Music control
    ├── clipboard.py       pbcopy / pbpaste
    ├── web_open.py        `open` URL handler
    ├── system_info.py     Battery, disk, network, CPU, uptime
    ├── voice.py           `say` TTS
    └── memory_tool.py     remember / recall / forget facts
```

## Deliberate omissions

- **Sending iMessages** — keeping iMessages strictly read-only. The risk
  surface for an LLM-driven SMS sender exceeds the convenience.
- **Voice input / wake word** — out of scope for a REPL.
- **Encryption at rest** — the memory store is plain JSON. Filesystem
  permissions are the right level for a personal CLI. Don't put secrets
  in there.

## Caveats

- macOS-only for the Apple integrations. The rest of the app runs anywhere.
- The audit log records *hashes* of tool results, not bodies, but the
  session JSON contains the full conversation including model responses.
  If you need PII-clean storage, delete the relevant session file or
  `/clear` before storing.
