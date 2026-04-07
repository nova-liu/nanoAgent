from pathlib import Path
import os

API_KEY = os.getenv("ARK_API_KEY")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
WORKDIR = Path.cwd()
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TASKS_DIR = WORKDIR / ".tasks"
SKILL_DIR = WORKDIR / "skills"
TEAM_DIR = WORKDIR / ".team"
HEARTBEAT_DIR = TEAM_DIR / "runtime"
HEARTBEAT_TTL_SECONDS = int(os.getenv("TEAM_HEARTBEAT_TTL_SECONDS", "8"))
INBOX_DIR = TEAM_DIR / "inbox"

# Ensure directories exist
TEAM_DIR.mkdir(parents=True, exist_ok=True)
INBOX_DIR.mkdir(parents=True, exist_ok=True)
HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
