# Troubleshooting

### Health check never passes / container restarts
- The app must listen on `:8080` and serve `/health`. Check logs:
  `docker compose logs challenge-ui`.
- The healthcheck uses Python's `urllib` against `127.0.0.1:8080/health`.

### `http://127.0.0.1:8080` refuses connection
- Port publishing comes from `docker-compose.override.yml`. Ensure it is
  present and not disabled with `-f docker-compose.yml` only.
- Confirm the container is `healthy`: `docker compose ps`.
- The base network is `internal: true`, which has no host route, so a published
  port cannot be reached through it alone. The override attaches a non-internal
  `dev-access` bridge network for this reason. If `docker compose ps` shows only
  `8080/tcp` (no `127.0.0.1:8080->8080`), the override/bridge did not apply —
  recreate with `docker compose up -d`.

### Submissions always return 422
- `422` means a malformed answer. Check the expected shape:
  - T3 needs a valid IP, T4 an integer.
  - T5 needs `{"first","last"}` ISO 8601 with a timezone (`...Z`).
  - T6/T7 need `{"choice", ...}` with a value from the allowed options.

### Validator can't find ground truth (`FileNotFoundError`)
- In compose, ground truth is mounted at `/run/secrets/ground_truth.yaml`
  (`GROUND_TRUTH_PATH`). Confirm `config/ground_truth.yaml` exists on the host.
- Running tests locally uses the default `config/ground_truth.yaml` path.

### Score didn't increase after a correct answer
- Points are awarded once per task. Re-submitting a solved task won't add score.
- Confirm you are on the same session (`X-Session-Id` header in dev).

### `429 attempt limit reached`
- You hit the per-task attempt cap (default 10). Use `POST /api/session/reset`
  (or the Reset button) to start over in dev.

### Read-only filesystem errors on write
- The container rootfs is read-only by design. Only `/tmp` (tmpfs) is writable.
  The app does not write to disk at runtime.

### Changing the dataset
- Edit `dataset/windows_security_events.json` AND `config/ground_truth.yaml`
  together, bump `dataset_version` in both, then run
  `python scripts/validate-dataset.py` and `pytest` before rebuilding.
