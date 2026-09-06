# nano-harness

A minimal coding-agent harness in Python, written while studying the Claude Code source code. It distills the core agentic loop — *model calls a tool, we run it, feed the result back, repeat* — into a single readable file with no framework on top.

## What it does

Give it a task and it works like a tiny coding agent:

- The model decides what shell commands to run via a single `bash` tool.
- Commands execute locally in the project directory.
- Output streams back to the model, which keeps acting until it decides it is done.

That loop is the heart of every agent harness, and this project exists to make it easy to see, poke at, and rebuild from scratch.

## Features

- **One tool, no abstraction**: `bash` only — the model sees one tool definition, and tool execution is one function ([src/agent.py](src/agent.py)).
- **Minimal guardrails** so you can experiment safely while learning:
  - dangerous-command blocklist (`rm -rf /`, `sudo`, `shutdown`, ...)
  - 120-second timeout per command
  - output capped at 50 KB before it goes back to the model
- **Interactive REPL** (`s01 >>`): type a question, watch each tool call as it happens, `q` to quit.
- **Provider-agnostic**: works with Anthropic or any Anthropic-compatible provider through `ANTHROPIC_BASE_URL` (MiniMax, GLM, Kimi, DeepSeek, ...).
- **Chinese-input fix for macOS**: libedit/readline bindings that keep CJK input working in the terminal.

## Requirements

- Python 3.9+
- An Anthropic API key, or an Anthropic-compatible provider endpoint

## Setup

```bash
git clone <repo-url>
cd nano-harness
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then edit in your API key and model
```

Environment variables (see [.env.example](.env.example) for provider list):

| Variable | Required | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | yes | API key |
| `MODEL_ID` | yes | Model to run the agent loop with |
| `ANTHROPIC_BASE_URL` | no | Endpoint override for Anthropic-compatible providers |

## Usage

```bash
python src/agent.py
```

Example session:

```
s01 >> fix the failing test in tests/test_math.py

$ pytest tests/test_math.py -x    # tool calls print in yellow
...
s01 >> q
```

## How it works

The whole idea fits in one loop ([src/agent.py:57](src/agent.py#L57)):

```
while True:
    response = client.messages.create(model, system, messages, tools)
    append response to history
    if response.stop_reason != "tool_use":
        return                 # model is done
    for each tool_use block:
        output = run_bash(command)
    append tool_result blocks to history   # loop continues
```

This is the same pattern Claude Code's agent loop builds on — the difference is everything else is stripped away. The system prompt is one line, the tool schema is hand-written JSON, and there is no planning, session management, or sandboxing layer yet. That is the point: each feature can be added back one at a time, on purpose, while reading how the real implementation does it.

## Project layout

```
src/agent.py        the entire harness: tools, execution, agent loop, REPL
.env.example        configuration template with Anthropic-compatible providers
requirements.txt    anthropic, python-dotenv, pyyaml
```

## Purpose and roadmap

This is a learning project: the author reads parts of the Claude Code source, then re-implements the pieces in this repo — small, honest, one concept per step (`s01`, `s02`, ...). Expected additions along the way:

- more tools (file read/write, glob, grep)
- multi-turn conversation persistence
- streaming responses
- permission prompts and confirmation flow
- hooks and subagents

If you are reading this as someone else: contributions welcome only if they keep the file count and concept-per-step philosophy intact.

## Safety notes

This is a teaching harness, not production software. The model runs arbitrary shell commands on your machine; the blocklist is a learning convenience, not a security boundary. Run it only in environments you trust with your own privileges, on code you do not mind being modified.

## License

None declared — contact the author before reusing.
