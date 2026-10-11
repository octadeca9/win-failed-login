"""Viewer-only mode (TASKS_ENABLED=false): dashboard served, tasks removed."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)


@pytest.fixture
def viewer_only():
    saved = config.TASKS_ENABLED
    config.TASKS_ENABLED = False
    yield
    config.TASKS_ENABLED = saved


def test_meta_hides_tasks(viewer_only):
    m = client.get("/api/meta").json()
    assert m["tasks_enabled"] is False
    assert m["tasks"] == []
    assert m["max_score"] == 0


def test_events_still_served(viewer_only):
    assert client.get("/api/events").json()["count"] > 0


def test_submit_disabled(viewer_only):
    r = client.post("/api/tasks/T1/submit", json={"answer": "4625"})
    assert r.status_code == 404


def test_session_endpoints_disabled(viewer_only):
    assert client.get("/api/session").status_code == 404
    assert client.post("/api/session/reset").status_code == 404


def test_readyz_needs_no_ground_truth(viewer_only):
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["mode"] == "viewer-only"


def test_index_omits_task_panel(viewer_only):
    html = client.get("/").text
    assert "Windows Security Event Log" in html   # dashboard present
    assert "Investigation tasks" not in html      # task panel gone
    assert "viewer-only" in html                  # full-width layout class


def test_tasks_enabled_by_default():
    # default mode still exposes tasks
    m = client.get("/api/meta").json()
    assert m["tasks_enabled"] is True
    assert len(m["tasks"]) == 8
