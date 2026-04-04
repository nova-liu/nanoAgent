from pathlib import Path
import os, json

API_KEY = os.getenv("ARK_API_KEY")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
WORKDIR = Path.cwd()
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TASKS_DIR = WORKDIR / ".tasks"
SKILL_DIR = WORKDIR / "skills"
TEAM_DIR = WORKDIR / ".team"
TEAM_CONFIG_PATH = TEAM_DIR / "config.json"
INBOX_DIR = TEAM_DIR / "inbox"
TEAM_CONFIG = json.loads(TEAM_CONFIG_PATH.read_text())
