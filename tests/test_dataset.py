"""Dataset schema + narrative consistency checks."""
from datetime import datetime

from app.services.loaders import load_dataset, load_ground_truth

REQUIRED_FIELDS = {
    "record_id", "event_id", "timestamp", "computer",
    "target_user", "source_ip", "logon_type", "status", "sub_status",
}


def _events():
    return load_dataset()["events"]


def test_all_events_have_schema_fields():
    for e in _events():
        assert REQUIRED_FIELDS.issubset(e.keys()), e


def test_record_ids_unique():
    ids = [e["record_id"] for e in _events()]
    assert len(ids) == len(set(ids))


def test_timestamps_are_iso_utc():
    for e in _events():
        ts = e["timestamp"]
        assert ts.endswith("Z")
        datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_only_4624_and_4625_present():
    assert {e["event_id"] for e in _events()} <= {4624, 4625}


def test_dataset_version_matches_ground_truth():
    assert load_dataset()["dataset_version"] == load_ground_truth()["dataset_version"]


def test_ground_truth_matches_dataset_counts():
    gt = load_ground_truth()["tasks"]
    user = gt["T2"]["expected"]
    ip = gt["T3"]["expected"]
    burst = [
        e for e in _events()
        if e["event_id"] == 4625 and e["target_user"] == user and e["source_ip"] == ip
    ]
    # T4: count matches
    assert len(burst) == gt["T4"]["expected"]
    # T2: target account truly has the most 4625 overall
    from collections import Counter
    fails = Counter(e["target_user"] for e in _events() if e["event_id"] == 4625)
    assert fails.most_common(1)[0][0] == user
    # T5: first/last timestamps match
    times = sorted(e["timestamp"] for e in burst)
    assert times[0] == gt["T5"]["first"]
    assert times[-1] == gt["T5"]["last"]
    # T6: a related 4624 success exists for same user+ip after the burst
    successes = [
        e for e in _events()
        if e["event_id"] == 4624 and e["target_user"] == user and e["source_ip"] == ip
    ]
    assert successes, "narrative requires a related successful logon"
    assert successes[0]["timestamp"] > times[-1]
