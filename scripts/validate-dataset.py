#!/usr/bin/env python3
"""Standalone dataset + ground-truth consistency checker.

Usage: python scripts/validate-dataset.py
Exits non-zero if the dataset narrative and ground truth disagree.
"""
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.loaders import load_dataset, load_ground_truth  # noqa: E402

REQUIRED = {
    "record_id", "event_id", "timestamp", "computer",
    "target_user", "source_ip", "logon_type", "status", "sub_status",
}


def main() -> int:
    ds = load_dataset()
    gt = load_ground_truth()
    events = ds["events"]
    errors = []

    for e in events:
        missing = REQUIRED - e.keys()
        if missing:
            errors.append(f"record {e.get('record_id')}: missing {missing}")
        try:
            datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
        except Exception:
            errors.append(f"record {e.get('record_id')}: bad timestamp {e['timestamp']}")

    if ds["dataset_version"] != gt["dataset_version"]:
        errors.append("dataset_version != ground_truth dataset_version")

    user = gt["tasks"]["T2"]["expected"]
    ip = gt["tasks"]["T3"]["expected"]
    burst = [e for e in events if e["event_id"] == 4625 and e["target_user"] == user and e["source_ip"] == ip]

    if len(burst) != gt["tasks"]["T4"]["expected"]:
        errors.append(f"T4 count mismatch: dataset={len(burst)} gt={gt['tasks']['T4']['expected']}")

    fails = Counter(e["target_user"] for e in events if e["event_id"] == 4625)
    if fails and fails.most_common(1)[0][0] != user:
        errors.append(f"T2 top-failed account mismatch: dataset={fails.most_common(1)[0][0]} gt={user}")

    times = sorted(e["timestamp"] for e in burst)
    if times and (times[0] != gt["tasks"]["T5"]["first"] or times[-1] != gt["tasks"]["T5"]["last"]):
        errors.append("T5 first/last timestamp mismatch")

    if errors:
        print("DATASET VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"OK: {len(events)} events, dataset {ds['dataset_version']}, narrative consistent with ground truth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
