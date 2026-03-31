#!/usr/bin/env sh
set -eu

log() {
  printf '[start_dev_stack] %s\n' "$1"
}

log "Bootstrapping Accessibility AI container"
log "Working directory: $(pwd)"

if [ ! -f /app/AccessBackEnd/manage.py ]; then
  log "ERROR: /app/AccessBackEnd/manage.py was not found"
  log "Diagnostic listing of /app:"
  find /app -maxdepth 3 -type f | sed -n '1,80p'
  exit 1
fi

if [ ! -f /app/AccessAppFront/package.json ]; then
  log "ERROR: /app/AccessAppFront/package.json was not found"
  log "Diagnostic listing of /app:"
  find /app -maxdepth 3 -type f | sed -n '1,80p'
  exit 1
fi

log "Initializing database and starting backend"
python3 /app/AccessBackEnd/manage.py --init-db --host 0.0.0.0 --port 5000 &
BACKEND_PID=$!

cleanup() {
  log "Stopping backend process ${BACKEND_PID}"
  kill "${BACKEND_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

log "Waiting for backend health check"
python3 - <<'PY'
import time
import urllib.request

url = "http://127.0.0.1:5000/api/v1/health"
last_error = None
for _ in range(60):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"[start_dev_stack] Backend health ready: {resp.status} {body[:200]}")
            raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(1)

print(f"[start_dev_stack] WARNING: backend health check did not pass in 60s: {last_error}")
PY

log "Starting frontend dev server"
npm --prefix /app/AccessAppFront run dev -- --host 0.0.0.0 --port 5173 --strictPort
