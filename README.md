# nano-harness

A self-contained **coding-agent harness** in pure Python — standard library only, no
third-party packages. One API key (`ANTHROPIC_API_KEY`) and it's ready.

Given a prompt, it can use a **tool-calling LLM** to edit files, run shell commands,
read the codebase, plan multi-step work, and **delegate to subagents and long-lived
autonomous teammates** coordinated through a shared, file-based task board and message
bus.

This is the capstone of a build-it-yourself series: a single `src/agent.py` that wraps
the Anthropic Messages API and stacks a real agent harness on top — structured tool
schemas, subagent delegation, persistent teammates, background command execution,
context compression, skill loading, and a REPL for live team orchestration.

---

## Features

- **Tool-calling loop** — sends prompt + tool definitions to Claude, dispatches each
  returned tool call, and feeds results back until a final text answer.
- **File & shell tools** — `bash`, `read_file`, `write_file`, `edit_file`, plus
  `background_run` for long jobs, all run in the working directory with a per-call
  timeout.
- **23 structured tools** — every tool is a JSON Schema `input_schema`; calls are
  validated and typed. See [`SCHEMAS.md`](SCHEMAS.md).
- **Subagent delegation** — spawn an isolated subagent with its own client/context to
  investigate a focused sub-task, keeping the parent's context clean.
- **Persistent teammates** — `spawn_teammate` starts autonomous teammates that run their
  own agent loop in a background thread, auto-claim tasks, and idle/poll when blocked.
- **Shared task board** — `.tasks/task_<id>.json` files with statuses, `blockedBy`
  dependency edges, owners, and atomic claiming.
- **Message bus** — a file-backed inbox (`BUS`) for typed teammate-to-teammate messaging,
  broadcasts, plan reviews, and shutdown handshakes.
- **Background execution** — long commands run in daemon threads; results can be injected
  asynchronously into the loop when they complete.
- **Two-tier context compression** — `microcompact` clears stale tool results;
  `auto_compact` summarizes the whole conversation into a structured summary when token
  usage crosses the threshold, preserving goals, constraints, todos, and decisions.
- **Skill loading** — Markdown skills with YAML frontmatter are discovered from a
  `skills/` tree and listed in the system prompt.
- **Resilient loop** — a stale "still working on it…" assistant reply is automatically
  followed by a "continue" nudge so the agent doesn't stall.

---

## Quick Start

```bash
cd nano-harness
export ANTHROPIC_API_KEY=sk-ant-...

python src/agent.py
```

This launches an **interactive REPL**: paste a prompt, watch the agent think and act,
repeat. Type `/exit` or press `Ctrl+C` to quit.

### REPL commands

| Command    | Effect                                             |
|------------|----------------------------------------------------|
| `/compact` | Force a context compaction                         |
| `/tasks`   | Print the task board                               |
| `/team`    | Print teammates and their statuses                 |
| `/inbox`   | Drain and print your inbox                         |

### Configuration

Everything is driven by environment variables:

| Variable           | Default                              | Purpose                          |
|--------------------|--------------------------------------|----------------------------------|
| `ANTHROPIC_API_KEY`| — (required)                         | Auth token for the Anthropic API |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com`        | API endpoint                     |
| `MODEL_ID`         | `claude-sonnet-4-6`                  | Model used by the lead agent     |

The working directory is the harness's own location (its parent of `src/`); all
workspace state is created under it:

```
.tasks/                # persistent task board
.team/                 # teammates.json, background_tasks.json, inbox/
.transcripts/          # auto_compact transcripts (.jsonl)
```

---

## How It Works

`main()` boots the harness, builds the system prompt, loads global singletons
(`TodoManager`, `SkillLoader`, `TaskManager`, `BackgroundManager`, `MessageBus`,
`TeammateManager`), and enters the REPL. Each turn calls `run_agent(prompt, messages)`,
which is the core loop:

> *build messages → call the API with all 23 tools → if the model returns
> `stop_reason == "tool_use"`, dispatch each block through `TOOL_HANDLERS` and append
> `tool_result` blocks → repeat until it returns plain text.*

A few guardrails keep the loop healthy:

- **Context budget** — `estimate_tokens()` (chars ÷ 4) is checked each turn; past
  `TOKEN_THRESHOLD` (100k) the conversation is micro-compacted and, if still too big,
  fully auto-compacted into a summary.
- **Nag reminder** — if the assistant replies with idle filler ("still working on it…"),
  a "Continue — do not stop with just a status update" nudge is appended and the loop
  retries.
- **Async background results** — between turns, any completed background command is
  surfaced to the model so it can react to it.

Two cooperating modules back the loop:

- `src/todo.py` — `TodoManager` enforces todo invariants (max 20 items, at most one
  `in_progress`, required `content`/`activeForm`) and renders a checkable list.
- `src/agent.py` — everything else: the API client, all 23 tools and their schemas, the
  tool dispatch table, subagents, teammates, the task board, the message bus, and
  compression.

---

## Tool Reference

The lead agent exposes **23 tools**, defined in `TOOLS` and dispatched by
`TOOL_HANDLERS`. Each is a JSON Schema `input_schema`; exact field definitions and
required parameters are in [`SCHEMAS.md`](SCHEMAS.md).

### Shell & files (5)
- `bash` — run a shell command (`command`, optional `timeout`).
- `read_file` — read a file (`path`, optional `limit`).
- `write_file` — create/overwrite a file (`path`, `content`).
- `edit_file` — replace an exact `old_text` with `new_text` in a file.
- `background_run` — run a command in a background thread (`command`, optional `timeout`),
  returns a `task_id`.

### Context (2)
- `compress` — force a context compaction (no args).
- `check_background` — check a background command's status (`task_id`).

### Task board (5)
- `task_create` — create a file task (`subject`, optional `description`).
- `task_get` — fetch one task by ID (`task_id`).
- `task_update` — change a task's `status` / dependencies (`task_id`, `status`,
  `add_blocked_by`, `remove_blocked_by`).
- `task_list` — list all tasks (no args).
- `claim_task` — atomically claim a task by ID (`task_id`).

### Planning & delegation (2)
- `TodoWrite` — set the in-memory todo list (`items`).
- `task` — spawn a subagent (`prompt`, optional `agent_type`).

### Skills (1)
- `load_skill` — load a skill by name (`name`).

### Team & messaging (5)
- `spawn_teammate` — start an autonomous teammate (`name`, `role`, `prompt`).
- `list_teammates` — list teammates and statuses (no args).
- `send_message` — send a typed message (`to`, `content`, optional `msg_type`).
- `read_inbox` — drain and read your inbox (no args).
- `broadcast` — send a message to all teammates (`content`).

### Lifecycle (2)
- `idle` — signal no more work (no args). For the lead this is a no-op.
- `shutdown_request` — ask a teammate to shut down (`teammate`).
- `plan_approval` — approve/reject a plan (`request_id`, `approve`, optional `feedback`).

> **Tool sets differ by role.** The lead uses the full `TOOLS` list above. Each teammate
> runs with a deliberately small, self-contained toolset of 7 tools — `bash`,
> `read_file`, `write_file`, `edit_file`, `send_message`, `idle`, and `claim_task` — so
> teammates stay focused on executing and coordinating, not re-planning the whole task.

---

## Subagent Delegation

The `task` tool spawns an isolated subagent for focused investigation:

- `agent_type: "Explore"` (default) — read-only investigation.
- `agent_type: "general-purpose"` — broader tool use.

The subagent runs its own loop against the same Anthropic client, so its context doesn't
pollute the parent's. Its final answer is returned as a `tool_result`.

---

## Persistent Teammates

`spawn_teammate` registers a teammate in `.team/teammates.json` and starts its own
agent loop in a daemon thread:

```
spawn_teammate(name="alice", role="code review", prompt="Review src/ for bugs")
```

Teammates run a **work/idle cycle**:

1. **Work phase** — drain the inbox, then loop on tool calls (up to 50 turns) until the
   model stops or calls `idle`.
2. **Idle phase** — mark itself `idle`, then poll every `POLL_INTERVAL` seconds (up to
   `IDLE_TIMEOUT`) for new inbox messages or **unclaimed, unblocked** tasks. Auto-claim
   picks up the first available one and resumes work.

Team state is shared through **files**, not memory:

- **Teammate registry** — `.team/teammates.json` tracks each member's `name`, `role`,
  and `status` (`working`, `idle`, `shutdown`).
- **Inbox** — the `MessageBus` writes messages as JSON files under `.team/inbox/`.
- **Task board** — `.tasks/task_<id>.json`, visible to everyone.

If a compressed teammate context loses its identity, the harness re-injects an
`<identity>` block before resuming.

### Message types

`send_message` supports a `msg_type` (default `message`): `message`, `broadcast`,
`shutdown_request`, `shutdown_response`, and `plan_approval_response`. Shutdown and plan
reviews carry a short `request_id` so responses can be matched to the original request.

---

## Task Board

Tasks live as JSON in `.tasks/`. `task_create` assigns a new ID and writes
`task_<id>.json`. A task carries a `status` (`pending` → `in_progress` → `completed`),
an optional `description`, an `owner`, and `blockedBy`/`blocks` dependency edges.

`claim_task` is atomic and refuses tasks that still have uncompleted blockers, so the
board enforces real dependency semantics across the team. See
[`SCHEMAS.md`](SCHEMAS.md) for the full task-record shape (below).

---

## Background Commands

`background_run` launches a long command in a daemon thread and immediately returns a
`task_id`. Poll `check_background(task_id)` for its output. Completed background tasks
are persisted in `.team/background_tasks.json`, and finished results are surfaced
asynchronously into the agent loop so the model can react without polling.

---

## Context Compression

Two layers keep the conversation under the token budget:

- **`microcompact`** — silently clears the content of all but the last 3 oversized
  tool results to `[cleared]`, recovering space cheaply.
- **`auto_compact`** — dumps the conversation to `.transcripts/transcript_<ts>.jsonl`,
  then asks the model for a structured summary covering goals, constraints, key
  decisions, the completed in-progress todo list, and file states.

The `/compact` REPL command and the `compress` tool trigger a compaction manually.

---

## Skills

Place skill files at `skills/<anything>/SKILL.md`. Each skill is a Markdown file with
optional YAML frontmatter (`name:`, `description:`, …) followed by the body. The
`SkillLoader` discovers them, lists them in the system prompt, and `load_skill` returns
the body wrapped in a `<skill>` block.

---

## Project Structure

```
nano-harness/
├── README.md            # this file
├── README-zh.md         # Chinese version
├── SCHEMAS.md           # tool input_schema + data-format reference
├── src/
│   ├── agent.py         # the full harness (tools, loop, team, tasks, compression)
│   └── todo.py          # TodoManager
└── .tasks/              # persistent task board (created at runtime)
```

---

## License

This project was built as part of the nano-harness coding-agent exercise. No license is
specified; see the source for attribution.
