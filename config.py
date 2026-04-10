from pathlib import Path
import os

# read from .env file if it exists
env_path = Path(".env")
if env_path.exists():
    with env_path.open() as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
WORKDIR = Path.cwd()
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
SKILL_DIR = WORKDIR / "skills"

# Ensure directories exist
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
SKILL_DIR.mkdir(parents=True, exist_ok=True)
