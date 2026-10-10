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

# Ground truth lives server-side only. In production this is supplied by the
# trusted validator service, NOT bundled into the participant image.
GROUND_TRUTH_PATH = Path(os.getenv("GROUND_TRUTH_PATH", _BASE / "config" / "ground_truth.yaml"))
