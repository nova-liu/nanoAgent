# nanoAgent

![logo](docs/logo.svg)

A multi-agent terminal collaboration experiment built on OpenAI-compatible Chat Completions.

This version focuses on three goals:

- The leader agent (nanoAgent) receives requests and orchestrates execution
- Persistent specialist agents can be spawned on demand
- Each task supports multi-round tool-call loops until a final response is produced

## Core Features

- Simple terminal REPL with stdout logging
- In-memory message bus (thread-safe Queue)
- Agent state visibility (idle/thinking/acting)
- Pluggable tool registry with profile-based assembly
- On-demand Skill loading from skills/\*\*/SKILL.md
- Conversation compaction and structured logging

## Quick Start

### Requirements

- Python 3.11+
- Environment variable OPENAI_API_KEY (for Volcengine API)

### Install and Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export OPENAI_API_KEY="your_api_key"
python main.py
```

Exit with quit, exit, or Ctrl+C.

## Usage

After startup, all plain text messages are sent to nanoAgent (leader).
nanoAgent chooses one of the following strategies:

- Handle the request directly
- Route to an online specialist
- Spawn a specialist first, then route
- Use sub_agent_task_tool for a one-off delegated task

### Built-in Commands

- quit/exit: Exit the app
- Ctrl+C: Exit the app

## Architecture Diagram

```mermaid
flowchart LR
    U[User]
    CLI[Terminal REPL\nmain.py]
    N[nanoAgent\nleader thread]
    MB[MessageBus\nin-memory queues]
    SP[spawned Agents\nspecialists]
    D[sub_agent_task_tool\none-off delegated agent]
    LLM[OpenAI Compatible\nChat Completions]
    TOOLS[Tools\nbash/read_file/write_file/edit_file/list_agents/send_message/compact/get_skill/sub_agent_task_tool/spawn]
    LOG[.transcripts/*\nstructured logs]
    SK[skills/**/SKILL.md]

    U --> CLI
    CLI -->|send text| MB
    MB -->|recv| N
    N <--> LLM
    N <--> TOOLS
    TOOLS --> SK
    N -->|spawn| SP
    N -->|delegate once| D
    SP -->|send_message| MB
    N -->|print logs| CLI
    SP -->|print logs| CLI
    N --> LOG
```

## Runtime Flow

1. The user enters a message in the terminal.
2. The REPL sends the message to nanoAgent via the message bus queue.
3. nanoAgent reads it from the queue and appends it to context.
4. nanoAgent starts a streaming LLM call; if tool calls are returned, tools are executed and tool results are fed back.
5. The loop continues until no more tool calls are returned.
6. Agents print tool activity, state changes, and replies directly to stdout.

## Project Structure

- main.py: Terminal REPL entry point
- agent.py: Agent loop and tool-call execution
- agent_context.py: Context and model parameter container
- agent_factory.py: Unified agent construction
- agent_profile.py: System templates and profile-based tool assembly
- agent_logger.py: LLM step logging (not currently used)
- client.py: OpenAI client setup
- config.py: Configuration and environment variables
- tools/: Tool implementations
  - tool.py: Tool abstraction
  - tool_bash.py: Bash command execution
  - tool_read_file.py: File reading
  - tool_write_file.py: File writing
  - tool_edit_file.py: File editing
  - tool_list_agents.py: List online agents
  - tool_send_message.py: Send messages between agents
  - tool_compact.py: Conversation compaction
  - tool_skill.py: Skill loading
  - tool_sub_agent_task.py: One-off delegated tasks
  - tool_spawn.py: Spawn new agents
  - tool_message_bus.py: Message bus implementation
- skills/: Skill directory
  - code-review/SKILL.md: Code review skill

## Tools

- bash: Execute shell commands
- read_file: Read file contents
- write_file: Write to files
- edit_file: Edit existing files
- list_agents: List online agents
- send_message: Send messages to other agents
- spawn: Spawn new specialist agents
- sub_agent_task_tool: Delegate one-off tasks
- get_skill: Load specialized knowledge
- compact: Compact conversation history

## Runtime Artifacts

- .transcripts/: Structured log archives
- .env: Environment variables (optional)

## Known Limitations

- bash currently has only basic risk filtering and is not a sandbox
- File tools do not yet enforce strict workspace-boundary checks
- run_loop uses a fixed 3-second polling interval
- End-to-end and tool-level test coverage is still limited

## Suggested Next Steps

1. Add path normalization and workspace-boundary enforcement for file tools
2. Add an allowlist mode for bash
3. Add a minimal E2E smoke test and core tool unit tests
