"""Load dataset and challenge/task/ground-truth configuration from disk."""
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


@lru_cache(maxsize=1)
def load_ground_truth() -> dict:
    """Server-side only. Never serialize this into any HTTP response."""
    return _read_yaml(config.GROUND_TRUTH_PATH)


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
