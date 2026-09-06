import os
import subprocess

try:
    import readline
    # macOS's libedit has a backspace issue when handling Chinese input; these four lines fix it.
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

# ── Tool definition: just bash ────────────────────────────
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string"
            }
        },
        "required": ["command"]
    }
}]

# ── Tool execution ────────────────────────────────────────
def run_bash(command: str) -> str:
    dangerous_commands = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(dangerous in command for dangerous in dangerous_commands):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, capture_output=True, cwd=os.getcwd(), text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OsError) as e:
        return f"Error: {e}"

# ── The core pattern: a while loop that calls tools until the model stops ──
def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages, tools=TOOLS, max_tokens=8000
        )

        messages.append({"role": "assistant", "content": response.content})

        # If the model didn't call a tool, we're done
        if response.stop_reason != "tool_use":
            return

        # Execute each tool call, collect results
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\033[33m$ {block.input['command']}\033[0m")
                output = run_bash(block.input["command"])
                print(output[:200])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })

        # Feed tool results back, loop continues
        messages.append({"role": "user", "content": results})

# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "quit", "exit"):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        # Print the model's final text response
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
        print()