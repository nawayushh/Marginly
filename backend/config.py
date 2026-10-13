"""
config.py - All settings for the Marginly backend live here.

Every other file imports its settings from this module instead of reading
environment variables itself. That way there is exactly one place to look
when you want to change a port, a timeout or a file path.

Values come from environment variables. For local development you put them
in backend/.env (copy .env.example to .env). Real environment variables
always win over the .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Folder that contains this file (marginly/backend) and the project root above it.
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Read backend/.env if it exists. A missing file is fine (defaults are used).
load_dotenv(BACKEND_DIR / ".env")


def _read_float(name: str, default: float) -> float:
    """Read a number from the environment; fall back to the default if it is missing or not a number."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# ---------------------------------------------------------------------------
# LM Studio / Qwen settings
# ---------------------------------------------------------------------------

# LM Studio's OpenAI-compatible server. YOUR port is 1235 (not LM Studio's usual 1234).
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1235/v1").strip()

# The model ID must match what LM Studio reports at GET {LM_STUDIO_BASE_URL}/models.
# It is deliberately empty by default: we never guess it. The AI health check
# (GET /api/ai/health) tells you clearly when it is missing.
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "").strip()

# LM Studio ignores the key, but the OpenAI SDK requires some value.
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio").strip()

# Seconds to wait for Qwen before giving up. A 9B model on a laptop can be slow.
AI_TIMEOUT_SECONDS = _read_float("AI_TIMEOUT_SECONDS", 120.0)

# ---------------------------------------------------------------------------
# Storage settings (SQLite)
# ---------------------------------------------------------------------------

# Where the SQLite database file is stored. Relative paths are resolved from the project root.
_db_setting = os.getenv("DATABASE_PATH", "data/marginly.db").strip()
DATABASE_PATH = Path(_db_setting)
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = PROJECT_ROOT / DATABASE_PATH

# Sample data used by "Load sample data".
SAMPLE_MENU_CSV = PROJECT_ROOT / "data" / "sample_menu.csv"

# ---------------------------------------------------------------------------
# Web server settings
# ---------------------------------------------------------------------------

# The only browser origin allowed to call the API (the Vite dev server).
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()

# Largest CSV upload we accept, in bytes (default 1 MB).
MAX_CSV_BYTES = int(_read_float("MAX_CSV_BYTES", 1_000_000))
