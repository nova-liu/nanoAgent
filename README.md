# nanoAgent

A small terminal-based coding agent built on top of the OpenAI-compatible Chat Completions API.

The project runs a main agent loop, supports tool calling, and can delegate subtasks to a sub-agent.

## Features

- Interactive terminal loop
- OpenAI-compatible chat completions client
- Function tools for shell, file IO, editing, todo management, and task delegation
- Main agent and sub-agent split
- Structured logging for model input, output, refusals, tool calls, and token usage

## Requirements

- Python 3.11+
- An API key exposed as `ARK_API_KEY`

## Setup

Create and activate a virtual environment, then install dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install openai rich
```

Set the API key:

```bash
export ARK_API_KEY="your_api_key"
```

## Run

Start the interactive loop:

```bash
python main.py
```

Example session:

```text
User: list files in the current folder
Agent: ...
```

Exit with `exit` or `quit`.

## Project Structure

- `main.py`: terminal entrypoint
- `agent.py`: main agent implementation and sub-agent orchestration
- `client.py`: API client configuration
- `tool_calls.py`: tool definitions and dispatch logic
- `todo_manager.py`: todo tool schema and in-memory todo manager
- `log.py`: logging helpers using `logging` and `rich`

## How It Works

### Conversation Loop

`main.py` reads user input and appends it to the main agent history.

`Agent.run_loop()` then:

1. Logs the current input history
2. Calls `client.chat.completions.create(...)`
3. Appends the assistant message back into the conversation
4. Executes tool calls if the model requested them
5. Appends tool outputs as `role="tool"` messages
6. Repeats until the model returns a normal final response

### Main Agent vs Sub-Agent

The main agent can call `task_tool` to delegate a subtask.

When that happens:

1. The main agent sends a prompt to the sub-agent
2. The sub-agent runs its own loop
3. The final sub-agent answer is returned as the tool result
4. The sub-agent history is reset after completion

## Tools

The current tool set includes:

- `bash`: run a shell command in the current working directory
- `read_file`: read a file from disk
- `write_file`: write a file to disk
- `edit_file`: replace content inside a file
- `todo_manager`: maintain a simple in-memory todo list
- `task_tool`: delegate a task to the sub-agent

## Client Configuration

The client is configured in `client.py` with an OpenAI-compatible base URL:

```python
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=api_key,
)
```

You can replace the base URL or model name if you want to target another compatible provider.

## Notes

- Tool execution is intentionally simple and local.
- `bash` blocks a small set of obviously dangerous commands, but this is not a hardened sandbox.
- The todo manager is in-memory only and is reset when the process exits.
- The current implementation uses chat completions, not the responses API.
