"""Structured logging helpers for chat.completions responses.

The module keeps existing function names so callers do not need to change code.
It uses ``logging`` and upgrades output with ``rich`` when available.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

LOGGER_NAME = "agent.log"
_console = Console()


def _get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = RichHandler(
        show_time=False, show_path=False, markup=True, rich_tracebacks=True
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(handler)
    return logger


def _pretty_json(text: str) -> str:
    try:
        return json.dumps(json.loads(text), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return text


def _truncate(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _extract_tool_call_names(tool_calls: Any) -> str:
    names: list[str] = []
    if not isinstance(tool_calls, list):
        return ""

    for tc in tool_calls:
        # dict-style tool calls from request payload history
        if isinstance(tc, dict):
            fn = tc.get("function")
            if isinstance(fn, dict) and fn.get("name"):
                names.append(str(fn["name"]))
            elif tc.get("name"):
                names.append(str(tc["name"]))
            else:
                names.append("unknown")
        else:
            # model objects
            fn = getattr(tc, "function", None)
            names.append(getattr(fn, "name", "unknown"))

    if not names:
        return ""
    return ", ".join(names)


def _message_preview(msg: dict[str, Any]) -> str:
    parts: list[str] = []

    content = msg.get("content")
    if isinstance(content, str) and content:
        parts.append(content)
    elif isinstance(content, list) and content:
        parts.append(f"[content_parts={len(content)}]")

    refusal = msg.get("refusal")
    if isinstance(refusal, str) and refusal:
        parts.append(f"[refusal] {refusal}")

    tool_calls = msg.get("tool_calls")
    if tool_calls:
        names = _extract_tool_call_names(tool_calls)
        if names:
            parts.append(f"[tool_calls] {names}")
        else:
            parts.append("[tool_calls]")

    # tool result message shape
    if msg.get("role") == "tool" and isinstance(content, str) and content:
        parts.append(f"[tool_result] {content}")

    # responses-style function_call_output shape (if mixed into history)
    if msg.get("type") == "function_call_output":
        output = msg.get("output")
        if output is not None:
            parts.append(f"[function_call_output] {output}")

    if not parts:
        parts.append("<no previewable fields>")

    return _truncate(" | ".join(parts), 240)


def log_input(messages: Iterable[dict[str, Any]]) -> None:
    """Log input messages grouped by role before sending a request."""
    logger = _get_logger()
    messages = list(messages)

    table = Table(title="Input Messages", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Role", width=12)
    table.add_column("Preview", overflow="fold")

    for i, msg in enumerate(messages):
        role = str(msg.get("role", "unknown"))
        preview = _message_preview(msg)
        table.add_row(str(i), role, preview)

    _console.print(Panel(table, border_style="cyan", title="USER INPUT / CONTEXT"))


def log_message(msg: Any) -> None:
    """Log one assistant message with separate sections by response type."""
    logger = _get_logger()

    content = getattr(msg, "content", None)
    refusal = getattr(msg, "refusal", None)
    tool_calls = getattr(msg, "tool_calls", None)
    annotations = getattr(msg, "annotations", None)
    audio = getattr(msg, "audio", None)

    if content:
        _console.print(Panel(str(content), title="MODEL: TEXT", border_style="green"))

    if refusal:
        _console.print(Panel(str(refusal), title="MODEL: REFUSAL", border_style="red"))

    if tool_calls:
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("#", style="dim", width=4)
        table.add_column("call_id", overflow="fold")
        table.add_column("name", style="yellow")
        table.add_column("arguments", overflow="fold")
        for i, tc in enumerate(tool_calls):
            fn = tc.function
            table.add_row(str(i), str(tc.id), str(fn.name), _pretty_json(fn.arguments))
        _console.print(Panel(table, title="MODEL: TOOL CALLS", border_style="yellow"))

    if annotations:
        log_annotations(annotations)

    if audio:
        log_audio(audio)


def log_tool_calls(tool_calls: Iterable[Any]) -> None:
    """Log parsed tool calls from a chat completion message."""
    logger = _get_logger()
    for i, tc in enumerate(tool_calls):
        fn = tc.function
        logger.info(
            "MODEL: TOOL_CALL[%s] id=%s %s(%s)",
            i,
            tc.id,
            fn.name,
            _pretty_json(fn.arguments),
        )


def log_usage(response: Any) -> None:
    """Log token usage for a full response object."""
    logger = _get_logger()
    usage = getattr(response, "usage", None)
    if not usage:
        return

    parts = [
        f"prompt={usage.prompt_tokens}",
        f"completion={usage.completion_tokens}",
        f"total={usage.total_tokens}",
    ]

    pd = getattr(usage, "prompt_tokens_details", None)
    if pd:
        cached = getattr(pd, "cached_tokens", None)
        if cached:
            parts.append(f"cached={cached}")

    cd = getattr(usage, "completion_tokens_details", None)
    if cd:
        reasoning = getattr(cd, "reasoning_tokens", None)
        if reasoning:
            parts.append(f"reasoning={reasoning}")

    logger.info("USAGE: %s", ", ".join(parts))


def log_response(response: Any, verbose: bool = False) -> None:
    """Log one full chat.completions response object."""
    logger = _get_logger()
    logger.info(
        "RESPONSE: model=%s id=%s choices=%s",
        response.model,
        response.id,
        len(response.choices),
    )
    log_usage(response)

    for i, choice in enumerate(response.choices):
        logger.info("CHOICE[%s]: finish_reason=%s", i, choice.finish_reason)
        log_message(choice.message)

    if verbose:
        log_raw(response)


def log_stream(stream: Iterable[Any]) -> str:
    """Log streaming deltas and return the merged text."""
    logger = _get_logger()
    full_text: list[str] = []
    refusal_text: list[str] = []
    tool_calls_buf: dict[int, dict[str, str]] = {}
    finish_reason = None
    model = None

    for chunk in stream:
        model = model or getattr(chunk, "model", None)
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            usage = getattr(chunk, "usage", None)
            if usage:
                _print_usage_obj(usage)
            continue

        delta = choices[0].delta
        fr = choices[0].finish_reason
        if fr:
            finish_reason = fr

        if delta.content:
            full_text.append(delta.content)

        if delta.refusal:
            refusal_text.append(delta.refusal)

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_buf:
                    tool_calls_buf[idx] = {"id": "", "name": "", "arguments": ""}
                buf = tool_calls_buf[idx]
                if tc_delta.id:
                    buf["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        buf["name"] += tc_delta.function.name
                    if tc_delta.function.arguments:
                        buf["arguments"] += tc_delta.function.arguments

    text = "".join(full_text)
    refusal = "".join(refusal_text)
    if text:
        _console.print(Panel(text, title="MODEL: STREAM TEXT", border_style="green"))

    if refusal:
        _console.print(
            Panel(refusal, title="MODEL: STREAM REFUSAL", border_style="red")
        )

    if tool_calls_buf:
        logger.info("STREAM SUMMARY: finish_reason=%s model=%s", finish_reason, model)
        for idx in sorted(tool_calls_buf):
            tc = tool_calls_buf[idx]
            logger.info(
                "STREAM TOOL_CALL[%s]: id=%s %s(%s)",
                idx,
                tc["id"],
                tc["name"],
                _pretty_json(tc["arguments"]),
            )
    elif finish_reason:
        logger.info("STREAM SUMMARY: finish_reason=%s model=%s", finish_reason, model)

    return text


def _print_usage_obj(usage: Any) -> None:
    logger = _get_logger()
    logger.info(
        "USAGE: prompt=%s, completion=%s, total=%s",
        usage.prompt_tokens,
        usage.completion_tokens,
        usage.total_tokens,
    )


def log_annotations(annotations: Iterable[Any]) -> None:
    """Log message annotations, including URL citations."""
    logger = _get_logger()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("type", width=16)
    table.add_column("details", overflow="fold")

    for ann in annotations:
        ann_type = getattr(ann, "type", "unknown")
        if ann_type == "url_citation":
            table.add_row(
                "url_citation", f"{ann.url_citation.title} -> {ann.url_citation.url}"
            )
        else:
            table.add_row(str(ann_type), "-")
    _console.print(Panel(table, title="MODEL: ANNOTATIONS", border_style="magenta"))


def log_audio(audio: Any) -> None:
    """Log a short audio response summary."""
    logger = _get_logger()
    transcript = getattr(audio, "transcript", "")
    preview = (transcript[:120] + "...") if len(transcript) > 120 else transcript
    logger.info("MODEL: AUDIO id=%s transcript=%s", getattr(audio, "id", ""), preview)


def log_raw(response: Any) -> None:
    """Log a full raw JSON dump for debugging."""
    logger = _get_logger()
    logger.info(
        "RAW RESPONSE JSON\n%s",
        json.dumps(response.model_dump(), indent=2, ensure_ascii=False, default=str),
    )
