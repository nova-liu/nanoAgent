"""
chat.completions response logging helpers
=========================================
Usage:
    from log import log_response, log_stream

    response = client.chat.completions.create(...)
    log_response(response)

    stream = client.chat.completions.create(stream=True, ...)
    log_stream(stream)    # Print deltas while collecting the full text.
"""

import json


# ── full response ─────────────────────────────────────


def log_response(response, verbose=False):
    """Print a completions response with text, tool calls, and refusals."""
    print(f"model={response.model}  id={response.id}")
    log_usage(response)

    for i, choice in enumerate(response.choices):
        prefix = f"[choice {i}] " if len(response.choices) > 1 else ""
        print(f"{prefix}finish_reason={choice.finish_reason}")
        log_message(choice.message)

    if verbose:
        log_raw(response)
    print()


# ── message ───────────────────────────────────────────


def log_message(msg):
    """Print the full contents of a single ChatCompletionMessage."""
    # Text response.
    if msg.content:
        print(f"[assistant] {msg.content}")

    # Refusal.
    if msg.refusal:
        print(f"[refusal] {msg.refusal}")

    # Tool calls.
    if msg.tool_calls:
        log_tool_calls(msg.tool_calls)

    # Annotations such as web search citations.
    annotations = getattr(msg, "annotations", None)
    if annotations:
        log_annotations(annotations)

    # Audio payload.
    audio = getattr(msg, "audio", None)
    if audio:
        log_audio(audio)


# ── tool calls ────────────────────────────────────────


def log_tool_calls(tool_calls):
    for i, tc in enumerate(tool_calls):
        fn = tc.function
        try:
            args = json.loads(fn.arguments)
            args_str = json.dumps(args, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            args_str = fn.arguments
        print(f"  [tool_call {i}] id={tc.id}  {fn.name}({args_str})")


# ── usage ─────────────────────────────────────────────


def log_usage(response):
    """Print token usage, including prompt cache and reasoning details."""
    usage = response.usage
    if not usage:
        return
    parts = [
        f"prompt={usage.prompt_tokens}",
        f"completion={usage.completion_tokens}",
        f"total={usage.total_tokens}",
    ]
    # Prompt details.
    pd = getattr(usage, "prompt_tokens_details", None)
    if pd:
        cached = getattr(pd, "cached_tokens", None)
        if cached:
            parts.append(f"cached={cached}")
    # Completion details.
    cd = getattr(usage, "completion_tokens_details", None)
    if cd:
        reasoning = getattr(cd, "reasoning_tokens", None)
        if reasoning:
            parts.append(f"reasoning={reasoning}")
    print(f"tokens: {', '.join(parts)}")


# ── streaming ─────────────────────────────────────────


def log_stream(stream):
    """Print text deltas chunk by chunk and summarize streamed tool calls."""
    full_text = []
    tool_calls_buf = {}  # index -> {id, name, arguments}
    finish_reason = None
    model = None

    for chunk in stream:
        model = model or chunk.model
        if not chunk.choices:
            # The final chunk may contain usage only.
            if chunk.usage:
                _print_usage_obj(chunk.usage)
            continue

        delta = chunk.choices[0].delta
        fr = chunk.choices[0].finish_reason
        if fr:
            finish_reason = fr

        # Text delta.
        if delta.content:
            print(delta.content, end="", flush=True)
            full_text.append(delta.content)

        # Tool call delta.
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

    # End the streamed text line.
    if full_text:
        print()

    # Summarize tool calls.
    if tool_calls_buf:
        print(f"finish_reason={finish_reason}  model={model}")
        for idx in sorted(tool_calls_buf):
            tc = tool_calls_buf[idx]
            try:
                args = json.dumps(json.loads(tc["arguments"]), ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                args = tc["arguments"]
            print(f"  [tool_call {idx}] id={tc['id']}  {tc['name']}({args})")
    elif finish_reason:
        print(f"finish_reason={finish_reason}  model={model}")

    return "".join(full_text)


def _print_usage_obj(usage):
    parts = [
        f"prompt={usage.prompt_tokens}",
        f"completion={usage.completion_tokens}",
        f"total={usage.total_tokens}",
    ]
    print(f"tokens: {', '.join(parts)}")


# ── annotations ───────────────────────────────────────


def log_annotations(annotations):
    """Print web search citation annotations."""
    for ann in annotations:
        ann_type = getattr(ann, "type", "unknown")
        if ann_type == "url_citation":
            print(f"  [citation] {ann.url_citation.title} — {ann.url_citation.url}")
        else:
            print(f"  [annotation] type={ann_type}")


# ── audio ─────────────────────────────────────────────


def log_audio(audio):
    """Print a short summary of the audio response."""
    print(f"  [audio] id={audio.id}  transcript={audio.transcript[:80]}...")


# ── raw dump ──────────────────────────────────────────


def log_raw(response):
    """Print the full raw JSON response for debugging."""
    print("--- raw response ---")
    print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False, default=str))


def log_input(messages):
    for i, msg in enumerate(messages):
        print(f"[message {i}] role={msg['role']} content={msg.get('content', '')[:80]}...")