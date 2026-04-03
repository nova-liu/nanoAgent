"""log.py – Agent flow visualization

Turn-by-turn display of LLM calls, tool dispatches, sub-agent delegation,
and token usage. Zero external dependencies (ANSI colors + box drawing).
"""

import json
import os
import sys
import ast
import re

# ── ANSI helpers ────────────────────────────────────────────────────────────


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _supports_color()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _bold(t: str) -> str:
    return _c("1", t)


def _dim(t: str) -> str:
    return _c("2", t)


def _cyan(t: str) -> str:
    return _c("36", t)


def _green(t: str) -> str:
    return _c("32", t)


def _yellow(t: str) -> str:
    return _c("33", t)


def _magenta(t: str) -> str:
    return _c("35", t)


def _red(t: str) -> str:
    return _c("31", t)


def _bold_cyan(t: str) -> str:
    return _c("1;36", t)


def _bold_green(t: str) -> str:
    return _c("1;32", t)


def _bold_yellow(t: str) -> str:
    return _c("1;33", t)


def _bold_magenta(t: str) -> str:
    return _c("1;35", t)


def _bold_red(t: str) -> str:
    return _c("1;31", t)


# ── Utilities ───────────────────────────────────────────────────────────────


def _trunc(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    text = _to_log_text(text).strip().replace("\n", "\\n")
    return text if len(text) <= max_len else text[:max_len] + "…"


def _decode_bytes(value: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "gbk", "latin-1"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")


def _decode_python_bytes_literal(text: str):
    stripped = text.strip()
    if not re.fullmatch(r"[bB][rR]?([\"']).*\1", stripped, re.DOTALL):
        return None
    try:
        literal = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return None
    if isinstance(literal, bytes):
        return _decode_bytes(literal)
    return None


def _decode_escaped_text(text: str) -> str:
    if "\\x" not in text and "\\u" not in text and "\\n" not in text:
        return text

    try:
        decoded = bytes(text, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return text

    # Keep the original if decoding would introduce control chars beyond whitespace.
    if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in decoded):
        return text
    return decoded


def _to_log_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return _decode_bytes(bytes(value))
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return str(value)

    text = str(value)
    decoded_literal = _decode_python_bytes_literal(text)
    if decoded_literal is not None:
        return decoded_literal
    return _decode_escaped_text(text)


_ROLE_ICON = {"system": "⚙️ ", "user": "👤", "assistant": "🤖", "tool": "🔧"}


# ── Box drawing ─────────────────────────────────────────────────────────────


def _box(title: str, lines: list[str], color_fn=_cyan, width: int = 68) -> str:
    """Draw a left-bordered Unicode box around content lines."""
    parts = []
    parts.append(
        color_fn(f"╭─ ")
        + color_fn(title)
        + " "
        + color_fn("─" * max(0, width - len(title) - 4))
    )

    for line in lines:
        for subline in line.split("\n"):
            parts.append(f"{color_fn('│')} {subline}")

    parts.append(color_fn("╰" + "─" * width))
    return "\n".join(parts)


# ── Logger ──────────────────────────────────────────────────────────────────


class AgentLogger:
    """Tracks and visualizes the agent loop execution flow."""

    def __init__(self):
        self._prev_count: dict[str, int] = {}
        self._turn: dict[str, int] = {}
        self._stack: list[str] = []
        self._tc_names: dict[str, str] = {}  # tool_call_id → function name

    @property
    def _depth(self) -> int:
        return max(len(self._stack) - 1, 0)

    def _indent(self) -> str:
        return "  │ " * self._depth

    # ── Message preview ─────────────────────────────────────────────────────

    def _msg_preview(self, msg: dict) -> str:
        role = msg.get("role", "?")
        content = msg.get("content", "")

        if role == "system":
            return _dim(_trunc(content, 60))
        elif role == "tool":
            tid = msg.get("tool_call_id", "")
            name = self._tc_names.get(tid, tid[:12])
            return f"{_cyan(name)} → {_trunc(content, 120)}"
        elif role == "assistant":
            tc = msg.get("tool_calls")
            if tc:
                names = [t.get("function", {}).get("name", "?") for t in tc]
                return _dim(f"(calls: {', '.join(names)})")
            return _trunc(content, 200) if content else _dim("(empty)")
        else:
            return _trunc(content, 200)

    def _format_tool_call(self, tc, index: int) -> str:
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments)
            parts = [f"{k}={_trunc(v, 80)}" for k, v in args.items()]
            args_str = ", ".join(parts)
        except (json.JSONDecodeError, AttributeError):
            args_str = _trunc(tc.function.arguments, 120)

        if name == "task_tool":
            line = f"  {_bold_magenta(f'{index}.')} {_bold_magenta(name)}({args_str})"
            line += f"\n     {_dim('↳ delegating to sub-agent …')}"
            return line
        return f"  {_cyan(f'{index}.')} {_cyan(name)}({args_str})"

    # ── Public API ──────────────────────────────────────────────────────────

    def log_messages(self, agent_name: str, messages: list):
        """Called before each LLM call."""
        # Stack management
        if not self._stack or self._stack[-1] != agent_name:
            self._stack.append(agent_name)
            if len(self._stack) > 1:
                ind = self._indent()
                print(f"\n{ind}{_bold_magenta('┌── Entering ' + agent_name + ' ──')}")

        # Turn tracking
        if agent_name not in self._turn:
            self._turn[agent_name] = 0
            self._prev_count[agent_name] = 0
        self._turn[agent_name] += 1
        turn = self._turn[agent_name]

        prev = self._prev_count.get(agent_name, 0)
        if len(messages) < prev:
            prev = 0  # messages were re-initialized
        new_msgs = messages[prev:]
        self._prev_count[agent_name] = len(messages)

        ind = self._indent()
        is_sub = len(self._stack) > 1
        color_fn = _magenta if is_sub else _cyan
        label_fn = _bold_magenta if is_sub else _bold_cyan

        # Build display lines
        lines = []
        if turn == 1:
            for m in messages:
                icon = _ROLE_ICON.get(m.get("role", ""), "?")
                role = m.get("role", "?")
                lines.append(f"  {icon} {role:10s}  {self._msg_preview(m)}")
        else:
            earlier = len(messages) - len(new_msgs)
            lines.append(f"  {_dim(f'… {earlier} earlier messages')}")
            for m in new_msgs:
                icon = _ROLE_ICON.get(m.get("role", ""), "?")
                role = m.get("role", "?")
                lines.append(f"  {icon} {role:10s}  {self._msg_preview(m)}")

        lines.append("")
        lines.append(f"  {_bold_yellow('▶ Calling LLM')}  ({len(messages)} msgs)")

        title = f"{agent_name} · turn {turn}"
        output = _box(title, lines, color_fn=color_fn)

        # Indent for sub-agents
        if is_sub:
            output = "\n".join(ind + line for line in output.split("\n"))

        print(f"\n{output}")

    def log_response(self, agent_name: str, response):
        """Called after each LLM response."""
        choice = response.choices[0] if response.choices else None

        # Cache tool_call_id → function name
        if choice and choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                self._tc_names[tc.id] = tc.function.name

        ind = self._indent()
        is_sub = len(self._stack) > 1
        is_final = choice and choice.finish_reason != "tool_calls"

        if not choice:
            print(f"{ind}  {_bold_red('✗ Empty response')}")
            return

        msg = choice.message
        finish = choice.finish_reason
        lines = []

        # Finish reason
        if finish == "tool_calls":
            lines.append(f"  {_bold_yellow('⚡ tool_calls')}")
        elif finish == "stop":
            lines.append(f"  {_bold_green('✔ stop')} {_dim('(final answer)')}")
        else:
            lines.append(f"  {_bold_red('⬤ ' + str(finish))}")

        # Content
        if msg.content:
            lines.append(f"  {_bold('Content:')} {_trunc(msg.content, 300)}")

        # Refusal
        if getattr(msg, "refusal", None):
            lines.append(f"  {_bold_red('Refusal:')} {msg.refusal}")

        # Tool calls
        if msg.tool_calls:
            lines.append("")
            for i, tc in enumerate(msg.tool_calls, 1):
                lines.append(self._format_tool_call(tc, i))

        # Usage
        usage = response.usage
        if usage:
            tok = (
                f"tokens: {usage.prompt_tokens} in · "
                f"{usage.completion_tokens} out · {usage.total_tokens} total"
            )
            lines.append("")
            lines.append(f"  {_dim(tok)}")

        color_fn = _green if finish == "stop" else _yellow
        output = _box("Response", lines, color_fn=color_fn)

        if is_sub:
            output = "\n".join(ind + line for line in output.split("\n"))

        print(output)

        # Pop stack when agent finishes
        if is_final:
            if self._stack and self._stack[-1] == agent_name:
                if len(self._stack) > 1:
                    print(f"{ind}{_bold_magenta('└── Leaving ' + agent_name + ' ──')}")
                self._stack.pop()
            self._turn.pop(agent_name, None)
            self._prev_count.pop(agent_name, None)


logger = AgentLogger()
