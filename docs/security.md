# Security & Trust Boundaries

## Core principle

The participant's browser and the participant's container are **untrusted**.
Scoring and the answer key live on the trusted side.

## What is where

| Asset | Location | Reachable by participant? |
|-------|----------|---------------------------|
| Dataset (`windows_security_events.json`) | participant image | yes (by design — no answers) |
| Public task definitions (`tasks.yaml`) | participant image | yes (no answers) |
| Ground truth (`ground_truth.yaml`) | trusted validator / read-only mount | **no** |
| Score / progress | server-side session store | read-only via API |

- The image build **excludes** `config/ground_truth.yaml` (`.dockerignore`),
  and the Dockerfile copies only `challenge.yaml` + `tasks.yaml`. In dev the
  ground truth is supplied via a read-only bind mount; in production it belongs
  to the trusted validator service, not the participant container.
- `/api/meta` and `/api/events` are asserted answer-key-free by tests
  (`test_scoring.py::test_meta_has_no_answers`, `test_events_...`).
- Incorrect submissions return a generic message and never echo the expected
  value (`test_incorrect_message_never_leaks_answer`).

## Container hardening (compose baseline)

- Non-root user (`uid 10001`).
- `read_only: true` root filesystem + `tmpfs: /tmp`.
- `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`.
- No `privileged`, no Docker socket mount, no host networking.
- `pids_limit`, `mem_limit`, `cpus` set; internal-only network.

## Scoring integrity

- Points are computed server-side and awarded once per task
  (`test_duplicate_correct_does_not_double_score`).
- Per-task attempt limit (default 10) blocks brute-forcing answers
  (`test_attempt_limit_enforced`).
- Sessions are isolated (`test_sessions_are_isolated`); production additionally
  enforces ownership at the gateway (IDOR protection), so the session ID is
  never accepted as proof of ownership.

## Checklist (maps to Blueprint §13)

- [x] Unique container per session (spawner responsibility at runtime)
- [x] No Windows/RDP dependency
- [x] Dataset contains only participant-visible info (RFC 5737 IPs, no PII)
- [x] Answer key absent from image/responses/filesystem
- [x] Non-root, dropped caps, no-new-privileges
- [x] No privileged mode / Docker socket / host network
- [ ] Egress default-deny + gateway auth — enforced at platform/host level
- [x] Rate/attempt limiting on submission
- [x] Resource limits + TTL
- [ ] Expiry/reset revokes access, cleanup removes resources — spawner duty
- [x] Logs omit tokens/answer key (structured logs, no secrets)
- [ ] Image scanned + pinned by digest before publish — CI duty
