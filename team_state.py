"""
Runtime team state — heartbeat is the single source of truth.

Each running agent writes a heartbeat file every few seconds.
An agent is "online" iff its heartbeat is fresh AND its pid is alive.
config.json is only used for historical reference; it is NOT authoritative.
"""

import json
import os
import time

from config import HEARTBEAT_DIR, HEARTBEAT_TTL_SECONDS


# ── heartbeat ──

def touch_heartbeat(name: str, role: str | None = None):
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "role": role,
        "pid": os.getpid(),
        "updated_at": time.time(),
    }
    (HEARTBEAT_DIR / f"{name}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )


def remove_heartbeat(name: str):
    path = HEARTBEAT_DIR / f"{name}.json"
    if path.exists():
        path.unlink(missing_ok=True)


def _read_heartbeat(name: str) -> dict | None:
    path = HEARTBEAT_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def _is_online(heartbeat: dict | None) -> bool:
    if not heartbeat:
        return False
    updated_at = heartbeat.get("updated_at")
    pid = heartbeat.get("pid")
    if not isinstance(updated_at, (int, float)):
        return False
    fresh = (time.time() - updated_at) <= HEARTBEAT_TTL_SECONDS
    return fresh and _pid_alive(pid)


# ── queries ──

def is_online(name: str) -> bool:
    return _is_online(_read_heartbeat(name))


def list_online_agents() -> list[dict]:
    """Return only agents that are confirmed alive right now."""
    if not HEARTBEAT_DIR.exists():
        return []
    agents = []
    for hb_file in sorted(HEARTBEAT_DIR.glob("*.json")):
        hb = _read_heartbeat(hb_file.stem)
        if _is_online(hb):
            agents.append({
                "name": hb["name"],
                "role": hb.get("role") or "unknown",
                "status": "online",
            })
    return agents


def list_all_agents() -> list[dict]:
    """Return all agents with heartbeat files, with online/offline status."""
    if not HEARTBEAT_DIR.exists():
        return []
    agents = []
    for hb_file in sorted(HEARTBEAT_DIR.glob("*.json")):
        hb = _read_heartbeat(hb_file.stem)
        if hb:
            online = _is_online(hb)
            agents.append({
                "name": hb["name"],
                "role": hb.get("role") or "unknown",
                "status": "online" if online else "offline",
            })
    return agents


def cleanup_stale_heartbeats():
    """Remove heartbeat files for agents whose pid is no longer alive."""
    if not HEARTBEAT_DIR.exists():
        return
    for hb_file in HEARTBEAT_DIR.glob("*.json"):
        hb = _read_heartbeat(hb_file.stem)
        if hb and not _pid_alive(hb.get("pid")):
            hb_file.unlink(missing_ok=True)