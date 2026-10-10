# API Contract

This lab's local endpoints mirror the conceptual platform contract. Align the
exact paths/auth with the official hack.redlimit.id API before production.

## Local (dev) endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness/readiness → `{"status":"ok"}` |
| GET | `/` | Log viewer UI |
| GET | `/api/meta` | Challenge metadata + public task definitions (no answers) |
| GET | `/api/events` | Participant-visible dataset |
| GET | `/api/session` | Progress + score for the current session |
| POST | `/api/session/reset` | Reset task progress |
| POST | `/api/tasks/{task_id}/submit` | Validate an answer (server-side) |

### Submit request/response

Scalar answer (T1–T4):

```json
POST /api/tasks/T1/submit
{ "answer": "4625" }
```

Structured answers:

```json
POST /api/tasks/T5/submit
{ "answer": { "first": "2026-10-09T02:14:05Z", "last": "2026-10-09T02:17:40Z" } }

POST /api/tasks/T6/submit
{ "answer": { "choice": "yes", "evidence": "4624" } }

POST /api/tasks/T7/submit
{ "answer": { "choice": "escalate", "priority": "high" } }
```

Response:

```json
{
  "correct": true,
  "task_id": "T1",
  "points_awarded": 2,
  "progress": { "completed": 1, "total": 7 },
  "score": 2,
  "max_score": 14,
  "status": "running",
  "attempts": 1,
  "attempts_remaining": 9,
  "message": "Correct."
}
```

Status codes: `200` validated (see `correct`), `404` unknown task, `422`
malformed answer (never reveals the expected value), `429` attempt limit
reached.

> In dev the session is bound to `SESSION_ID`; send `X-Session-Id: <name>` to
> simulate multiple isolated sessions. In production the gateway injects an
> authenticated, ownership-verified session reference — the session ID is never
> trusted as proof of ownership.

## Platform contract (conceptual)

- `POST /api/challenges/{slug}/sessions` → create session (idempotency key)
- `GET /api/challenge-sessions/{session_id}` → status/progress/score
- `POST /api/challenge-sessions/{session_id}/tasks/{task_id}/submit`
- `POST /api/challenge-sessions/{session_id}/reset`

Rules: TLS, authn/authz on every request, ownership checks beyond the session
ID, rate limits on start/reset/submit, idempotent start/reset, schema+size
validation, server-side scoring only, answer key never sent to the browser,
short-lived revocable container-access tokens.
