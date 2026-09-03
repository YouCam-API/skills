"""Shared constants and path resolution for the youcam_core scripts.

- `SKILL_SCRIPT_ROOT` is this `scripts/` folder in a agent skill.
- Everything the engine reads/writes lives here except credentials.json, which stays one level up
(a skill's root next to SKILL.md) instead of following the code.
"""

import os

SKILL_SCRIPT_ROOT = os.path.dirname(os.path.abspath(__file__))
API_FALLBACK_DOC = os.path.join(SKILL_SCRIPT_ROOT, "api-fallback.yaml")
CREDENTIALS_FILE = os.path.join(os.path.dirname(SKILL_SCRIPT_ROOT), "credentials.json")

# Install dependencies into a local virtual environment in the skill script folder.
_VENV_DIR = os.path.join(SKILL_SCRIPT_ROOT, ".venv")
_REQUIREMENTS = os.path.join(SKILL_SCRIPT_ROOT, "requirements.txt")

TASK_STATUS = {"success", "error"}
SUPPORT_FILE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4"}

_REQUEST_TIMEOUT = 30  # seconds, for quick metadata/task status calls
_UPLOAD_TIMEOUT = 300  # seconds, for the actual file PUT
_DEFAULT_POLL_INTERVAL = 5.0
_DEFAULT_MAX_POLLS = 20

DEFAULT_API_BALANCE_PATH = "/s2s/v1.0/client/credit"
DEFAULT_API_FEAT_COST_PATH = "/s2s/v2.0/credit/feature-cost"
DEFAULT_UPLOAD_PATH = "/s2s/v2.0/file"
