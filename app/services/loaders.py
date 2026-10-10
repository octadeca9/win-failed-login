"""Load dataset and challenge/task/ground-truth configuration."""
import base64
import binascii
import json
from functools import lru_cache
from pathlib import Path

import yaml

from app import config


def _read_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def load_dataset() -> dict:
    with open(config.DATASET_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_challenge() -> dict:
    return _read_yaml(config.CHALLENGE_CONFIG_PATH)


@lru_cache(maxsize=1)
def load_tasks() -> list[dict]:
    return _read_yaml(config.TASKS_CONFIG_PATH).get("tasks", [])


class GroundTruthNotConfigured(RuntimeError):
    """Raised when no ground-truth source is available."""


@lru_cache(maxsize=1)
def load_ground_truth() -> dict:
    """Server-side only. Never serialize this into any HTTP response.

    Resolved in order: GROUND_TRUTH_B64 -> GROUND_TRUTH_YAML -> file at
    GROUND_TRUTH_PATH. This lets env-only platforms (e.g. ngelinx) inject the
    answer key at runtime without baking it into the image.
    """
    if config.GROUND_TRUTH_B64:
        try:
            raw = base64.b64decode(config.GROUND_TRUTH_B64, validate=True).decode("utf-8")
        except (binascii.Error, ValueError) as exc:
            raise GroundTruthNotConfigured(
                "GROUND_TRUTH_B64 is set but is not valid base64"
            ) from exc
        return yaml.safe_load(raw)

    if config.GROUND_TRUTH_YAML:
        return yaml.safe_load(config.GROUND_TRUTH_YAML)

    if config.GROUND_TRUTH_PATH.exists():
        return _read_yaml(config.GROUND_TRUTH_PATH)

    raise GroundTruthNotConfigured(
        "No ground truth configured. Set GROUND_TRUTH_B64 (recommended for "
        "env-only platforms) or GROUND_TRUTH_YAML, or mount a file at "
        f"{config.GROUND_TRUTH_PATH} and set GROUND_TRUTH_PATH."
    )


def public_tasks() -> list[dict]:
    """Task metadata safe to send to the browser (no answers)."""
    out = []
    for t in load_tasks():
        out.append(
            {
                "id": t["id"],
                "section_id": t["section_id"],
                "title": t["title"],
                "points": t["points"],
                "validator_type": t["validator_type"],
                "sort_order": t["sort_order"],
                "instructions": " ".join(t["instructions"].split()),
                "input": t.get("input", "text"),
                "answer_hint": t.get("answer_hint"),
                "evidence_hint": t.get("evidence_hint"),
                "choices": t.get("choices"),
                "priorities": t.get("priorities"),
                "require_evidence": t.get("require_evidence", False),
                "require_priority": t.get("require_priority", False),
            }
        )
    return out
