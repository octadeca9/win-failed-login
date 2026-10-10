# Windows Failed Login Investigation — SOC Analyst Lab

SOC Analyst (Easy) challenge for **hack.redlimit.id**. Participants analyse a
synthetic Windows Security Event Log (Event IDs `4625` / `4624`), identify a
suspicious authentication pattern, and submit a triage verdict.

- **1 section · 8 tasks · 500 points (difficulty-weighted) · ~15–20 min**
- No Windows VM, no RDP, no full SIEM. Offline JSON dataset + web log viewer.
- Server-side validation; ground truth never reaches the browser or the
  participant image.

Built from `PRD_Windows_Failed_Login_SOC_RedLimit.md` and
`Blueprint_Windows_Failed_Login_SOC_RedLimit.md`.

## Quick start (local)

```bash
cp .env.example .env            # optional
docker compose up --build       # override publishes 127.0.0.1:8080
```

Open <http://127.0.0.1:8080>. The `docker-compose.override.yml` maps the port on
loopback for local testing only — production access goes through the platform
gateway, not a published port.

### Run tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                      # unit + API tests
python scripts/validate-dataset.py   # dataset vs ground-truth consistency
```

### End-to-end smoke test

```bash
./scripts/local-smoke-test.sh
```

## The 8 tasks

| ID | Title | Validator | Points |
|----|-------|-----------|-------:|
| T1 | Identify Failed Logon Events | exact_match (Event ID) | 20 |
| T2 | Find the Target Account | normalized_string | 45 |
| T3 | Identify the Source IP | ip_match (canonical) | 45 |
| T4 | Count Failed Attempts | integer_match | 60 |
| T5 | Find the Attempt Window | timestamp_window (ISO 8601 UTC) | 70 |
| T6 | Check for a Successful Logon | structured_choice + evidence | 90 |
| T7 | Submit the SOC Triage Verdict | structured_choice + priority | 140 |
| T8 | Analyze the Logon Type | integer_match (logon_type) | 30 |
| | | **Total** | **500** |

Points are difficulty-weighted (tens → hundreds). Scoring is server-side; the
weights live in `config/tasks.yaml` and the total is derived, not hard-coded.

## Architecture (dev baseline)

```
Browser ── HTTP ──> FastAPI app (app/main.py)
                      ├─ GET  /                 log viewer UI
                      ├─ GET  /api/meta         challenge + public tasks (no answers)
                      ├─ GET  /api/events       participant-visible dataset
                      ├─ POST /api/tasks/{id}/submit   server-side validation
                      ├─ GET  /api/session      progress + score
                      └─ POST /api/session/reset
                   validator (app/services/validator.py)
                      └─ reads config/ground_truth.yaml  (mounted read-only,
                         NOT baked into the image)
```

In production the validator/scoring runs as a trusted service and a spawner
creates one isolated container per session. See `docs/`.

## Layout

```
app/        FastAPI application (routes, services, templates, static)
config/     challenge.yaml, tasks.yaml (public) + ground_truth.yaml (server-side)
dataset/    windows_security_events.json (participant-visible, no answers)
tests/      pytest suite (dataset, validator, scoring/API)
scripts/    validate-dataset.py, local-smoke-test.sh
docs/       deployment, api-contract, security, troubleshooting
```

> This is a development baseline + reference implementation. Align the API
> contract, gateway, and spawner with the real hack.redlimit.id platform before
> production. See `docs/security.md` for the trust-boundary notes.
