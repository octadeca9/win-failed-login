# Deployment

## Development (Docker Compose)

```bash
docker compose up --build
```

- `docker-compose.yml` is the hardened baseline: `read_only` rootfs, `tmpfs`
  `/tmp`, all capabilities dropped, `no-new-privileges`, non-root user,
  `pids_limit=100`, `mem_limit=256m`, `cpus=0.5`, internal-only network, and a
  `/health` healthcheck.
- `docker-compose.override.yml` publishes `127.0.0.1:8080` for local browser
  access. Compose auto-merges it. **Do not deploy the override to production.**
- Ground truth is provided via a read-only bind mount
  (`./config/ground_truth.yaml:/run/secrets/ground_truth.yaml:ro`) and is
  **excluded from the image** (`.dockerignore`). This simulates the
  trusted-store separation.

Build the production image without the answer key:

```bash
docker build -t redlimit/windows-failed-login:1.0.0 .
# verify the answer key is NOT in the image:
docker run --rm redlimit/windows-failed-login:1.0.0 \
  sh -c 'ls config/ground_truth.yaml 2>/dev/null && echo LEAK || echo clean'
```

## Supplying the ground truth (answer key)

The validator needs the answer key at runtime, and it must never be baked into
the image. The source is resolved in this order:

1. **`GROUND_TRUTH_B64`** — base64 of `config/ground_truth.yaml`. Recommended
   for env-only platforms (e.g. **ngelinx**) that expose key/value variables but
   no file mounts. Generate the value with:
   ```bash
   base64 < config/ground_truth.yaml | tr -d '\n'
   ```
   Then set it as a single environment variable on the platform.
2. **`GROUND_TRUTH_YAML`** — the raw YAML content as the variable value.
3. **`GROUND_TRUTH_PATH`** — a file path (used by `docker-compose.yml`, which
   mounts the file read-only at `/run/secrets/ground_truth.yaml`).

If none is provided, task submission returns **HTTP 503** ("validator not
configured") and logs `ground_truth_not_configured` — this is the symptom when
neither a mount nor an env var is set (the image has no key by design).

## Runtime (Docker Spawn)

Docker Compose is a dev tool only. In production a spawner creates one container
per session from the pinned immutable image (`...@sha256:<digest>`):

- Labels: `redlimit.challenge`, `redlimit.session_id`, `redlimit.user_ref`
  (pseudonymous), `redlimit.expires_at`, `redlimit.managed_by`.
- Resource limits: CPU 0.5, memory 256 MiB, PID limit 100, session TTL 45 min.
- No `container_name` on runtime templates (blocks parallel sessions).
- Network: default-deny egress; access via the platform gateway with a
  short-lived, ownership-checked session token. No published host port.
- The trusted validator/scoring service runs outside the participant container;
  the participant image carries only dataset + UI.

### Lifecycle

```
start → authenticate/authorize → create session (provisioning)
      → spawn container → labels + resource/network policy
      → health check → ready → participant works
      → completed / expired / reset → revoke access + stop/remove container
```

Reset and cleanup must be idempotent. A reconciliation worker removes orphaned
containers/networks whose `expires_at` has passed.

## Health & readiness

The app serves `GET /health` → `{"status":"ok"}`. The container healthcheck
polls it; the spawner should treat `ready` only after the healthcheck passes.
