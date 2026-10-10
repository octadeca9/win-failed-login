"""Runtime configuration loaded from environment variables."""
import os
from pathlib import Path

APP_ENV = os.getenv("APP_ENV", "development")
CHALLENGE_SLUG = os.getenv("CHALLENGE_SLUG", "windows-failed-login-investigation")
PORT = int(os.getenv("PORT", "8080"))
SESSION_ID = os.getenv("SESSION_ID", "local-dev-session")

_BASE = Path(__file__).resolve().parent.parent

DATASET_PATH = Path(os.getenv("DATASET_PATH", _BASE / "dataset" / "windows_security_events.json"))
CHALLENGE_CONFIG_PATH = Path(os.getenv("CHALLENGE_CONFIG_PATH", _BASE / "config" / "challenge.yaml"))
TASKS_CONFIG_PATH = Path(os.getenv("TASKS_CONFIG_PATH", _BASE / "config" / "tasks.yaml"))

# Ground truth lives server-side only and must NOT be bundled into the
# participant image. It can be supplied three ways (checked in this order):
#   1. GROUND_TRUTH_B64  — base64-encoded YAML content (robust for env-only
#      platforms like ngelinx; avoids newline/quoting issues).
#   2. GROUND_TRUTH_YAML — raw YAML content in an environment variable.
#   3. GROUND_TRUTH_PATH — a file path (used by local docker-compose mount).
GROUND_TRUTH_B64 = os.getenv("GROUND_TRUTH_B64")
GROUND_TRUTH_YAML = os.getenv("GROUND_TRUTH_YAML")
GROUND_TRUTH_PATH = Path(os.getenv("GROUND_TRUTH_PATH", _BASE / "config" / "ground_truth.yaml"))
