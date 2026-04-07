"""
Lightweight event bus for decoupling agent runtime from UI rendering.

Events flow:  Agent threads  ──emit()──►  EventBus  ──►  UI subscriber

Event kinds:
  state_changed   agent entered a new state (idle/thinking/acting)
  stream_start    LLM streaming begins for an agent
  stream_delta    a chunk of streamed text
  stream_end      LLM streaming finished
  tool_start      agent is calling a tool
  tool_end        tool returned a result
  error           agent hit an exception
  bus_event       message bus activity (sent/received)
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Callable

# ── Agent states ──
IDLE = "idle"
THINKING = "thinking"
ACTING = "acting"


@dataclass
class Event:
    kind: str
    agent: str  # agent name
    data: dict = field(default_factory=dict)


# Global subscriber — set by the UI layer (cmd/main.py)
_subscriber: Callable[[Event], None] | None = None
_lock = threading.Lock()


def subscribe(fn: Callable[[Event], None]):
    global _subscriber
    with _lock:
        _subscriber = fn


def emit(kind: str, agent: str, **data):
    with _lock:
        fn = _subscriber
    if fn:
        fn(Event(kind=kind, agent=agent, data=data))
