from pathlib import Path
import os

API_KEY = os.getenv("ARK_API_KEY")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
WORKDIR = Path.cwd()
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
SKILL_DIR = WORKDIR / "skills"

# Ensure directories exist
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
SKILL_DIR.mkdir(parents=True, exist_ok=True)
