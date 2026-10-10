#!/usr/bin/env bash
# Build, start, and smoke-test the lab via docker compose.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Building and starting (compose + override)…"
docker compose up --build -d

cleanup() { echo "==> Tearing down…"; docker compose down -v; }
trap cleanup EXIT

echo "==> Waiting for /health…"
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "   healthy"
    break
  fi
  sleep 1
  [ "$i" -eq 30 ] && { echo "   health check timed out"; exit 1; }
done

echo "==> Checking meta leaks no answer key…"
if curl -fsS http://127.0.0.1:8080/api/meta | grep -qi "jsmith\|198.51.100.42"; then
  echo "   FAIL: answer key leaked via /api/meta"; exit 1
fi
echo "   ok"

echo "==> Submitting T1 (4625) …"
curl -fsS -X POST http://127.0.0.1:8080/api/tasks/T1/submit \
  -H 'Content-Type: application/json' -d '{"answer":"4625"}'
echo

echo "==> Smoke test passed."
