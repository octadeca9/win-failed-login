"""Windows Failed Login Investigation — challenge UI + server-side validator.

Development baseline (Docker Compose). In production the validator/scoring is a
trusted service and the spawner runs one container per participant session.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app import config
from app.services import validator
from app.services.loaders import (
    GroundTruthNotConfigured,
    load_challenge,
    load_dataset,
    public_tasks,
)
from app.services.session import store

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","event":"%(message)s"}',
)
logger = logging.getLogger("challenge")

_BASE = Path(__file__).resolve().parent

app = FastAPI(title="Windows Failed Login Investigation", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(_BASE / "templates"))

_static_dir = _BASE / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


class SubmitRequest(BaseModel):
    # answer may be a scalar (str/int) or a structured object (dict).
    answer: object = Field(...)


def _session_id(request: Request) -> str:
    """Dev baseline binds to a single configured session id.

    In production the gateway injects an authenticated, ownership-checked
    session reference; here we accept an optional header for multi-session
    local testing and otherwise fall back to the configured SESSION_ID.
    """
    return request.headers.get("X-Session-Id", config.SESSION_ID)


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    challenge = load_challenge()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "challenge": challenge,
            "narrative": " ".join(challenge.get("narrative", "").split()),
        },
    )


@app.get("/api/meta")
def meta() -> dict:
    challenge = load_challenge()
    return {
        "slug": challenge["slug"],
        "title": challenge["title"],
        "difficulty": challenge["difficulty"],
        "estimated_minutes": challenge["estimated_minutes"],
        "max_score": challenge["max_score"],
        "narrative": " ".join(challenge.get("narrative", "").split()),
        "sections": challenge["sections"],
        "tasks": public_tasks(),
    }


@app.get("/api/events")
def events() -> dict:
    """Participant-visible dataset. Contains no answer key."""
    ds = load_dataset()
    return {
        "dataset_version": ds.get("dataset_version"),
        "notice": ds.get("notice"),
        "timezone": ds.get("timezone"),
        "count": len(ds.get("events", [])),
        "events": ds.get("events", []),
    }


@app.get("/api/session")
def session_status(request: Request) -> dict:
    return store.status(_session_id(request))


@app.post("/api/session/reset")
def session_reset(request: Request) -> dict:
    sid = _session_id(request)
    logger.info('session_reset session=%s', sid)
    return store.reset(sid)


@app.post("/api/tasks/{task_id}/submit")
def submit(task_id: str, body: SubmitRequest, request: Request) -> dict:
    sid = _session_id(request)

    public_ids = {t["id"] for t in public_tasks()}
    if task_id not in public_ids:
        raise HTTPException(status_code=404, detail="unknown task")

    try:
        # Enforce attempt limits before spending a validation.
        used = store.attempts_used(sid, task_id)
        limit = validator.max_attempts(task_id)
        if used >= limit:
            logger.info('attempts_exceeded session=%s task=%s', sid, task_id)
            raise HTTPException(status_code=429, detail="attempt limit reached for this task")

        result = validator.validate(task_id, body.answer)
    except GroundTruthNotConfigured as exc:
        # Misconfiguration, not a participant error. Surface clearly, don't
        # consume an attempt, and log for the operator.
        logger.error('ground_truth_not_configured: %s', exc)
        raise HTTPException(status_code=503, detail="validator not configured; contact the lab operator")
    except validator.ValidationError as exc:
        # Malformed answer does not consume... actually record it as an attempt
        # to prevent unbounded probing, but never leak the expected value.
        store.record_attempt(sid, task_id, correct=False)
        raise HTTPException(status_code=422, detail=str(exc))

    outcome = store.record_attempt(sid, task_id, result.correct)
    logger.info(
        'task_submit session=%s task=%s correct=%s attempts=%s',
        sid, task_id, result.correct, outcome["attempts"],
    )
    outcome["message"] = result.message
    outcome["attempts_remaining"] = max(0, limit - outcome["attempts"])
    return outcome
