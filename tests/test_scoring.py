"""Scoring/session + HTTP endpoint behavior."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _sid(name):
    return {"X-Session-Id": name}


def setup_function():
    # isolate each test with its own session id reset
    pass


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_readyz_reports_ground_truth_loaded():
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["ground_truth_loaded"] is True
    assert body["task_count"] == 8
    # diagnostics must never leak the answer key
    assert "jsmith" not in r.text.lower()
    assert "4625" not in r.text


def test_meta_has_no_answers():
    body = client.get("/api/meta").text.lower()
    assert "jsmith" not in body
    assert "198.51.100.42" not in body


def test_events_contains_no_ground_truth_fields():
    data = client.get("/api/events").json()
    assert data["count"] == len(data["events"])
    assert "expected" not in client.get("/api/events").text


def test_full_solve_reaches_14():
    h = _sid("solve-session")
    client.post("/api/session/reset", headers=h)
    answers = {
        "T1": "4625",
        "T2": "jsmith",
        "T3": "198.51.100.42",
        "T4": "12",
        "T5": {"first": "2026-10-09T02:14:05Z", "last": "2026-10-09T02:17:40Z"},
        "T6": {"choice": "yes", "evidence": "4624"},
        "T7": {"choice": "escalate", "priority": "high"},
        "T8": "3",
    }
    last = None
    for tid, ans in answers.items():
        r = client.post(f"/api/tasks/{tid}/submit", json={"answer": ans}, headers=h)
        assert r.status_code == 200, r.text
        last = r.json()
        assert last["correct"] is True
    assert last["score"] == 500
    assert last["max_score"] == 500
    assert last["progress"] == {"completed": 8, "total": 8}
    assert last["status"] == "completed"


def test_duplicate_correct_does_not_double_score():
    h = _sid("dup-session")
    client.post("/api/session/reset", headers=h)
    client.post("/api/tasks/T1/submit", json={"answer": "4625"}, headers=h)
    r = client.post("/api/tasks/T1/submit", json={"answer": "4625"}, headers=h)
    body = r.json()
    assert body["score"] == 20  # only T1 (20 pts) counted once
    assert body["progress"]["completed"] == 1


def test_wrong_answer_does_not_leak_or_score():
    h = _sid("wrong-session")
    client.post("/api/session/reset", headers=h)
    r = client.post("/api/tasks/T2/submit", json={"answer": "administrator"}, headers=h)
    body = r.json()
    assert body["correct"] is False
    assert body["score"] == 0
    assert "jsmith" not in r.text.lower()


def test_malformed_answer_returns_422():
    h = _sid("malformed-session")
    client.post("/api/session/reset", headers=h)
    r = client.post("/api/tasks/T3/submit", json={"answer": "nope"}, headers=h)
    assert r.status_code == 422


def test_attempt_limit_enforced():
    h = _sid("limit-session")
    client.post("/api/session/reset", headers=h)
    # max_attempts is 10 for T1; 10 wrong answers then the 11th is blocked
    for _ in range(10):
        client.post("/api/tasks/T1/submit", json={"answer": "0000"}, headers=h)
    r = client.post("/api/tasks/T1/submit", json={"answer": "4625"}, headers=h)
    assert r.status_code == 429


def test_unknown_task_404():
    assert client.post("/api/tasks/T99/submit", json={"answer": "x"}).status_code == 404


def test_sessions_are_isolated():
    a, b = _sid("iso-a"), _sid("iso-b")
    client.post("/api/session/reset", headers=a)
    client.post("/api/session/reset", headers=b)
    client.post("/api/tasks/T1/submit", json={"answer": "4625"}, headers=a)
    assert client.get("/api/session", headers=a).json()["score"] == 20
    assert client.get("/api/session", headers=b).json()["score"] == 0
