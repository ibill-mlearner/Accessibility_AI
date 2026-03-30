#!/usr/bin/env bash
set -euo pipefail

cd /app/AccessAppFront
if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  npm ci
fi

cd /app/AccessBackEnd
python3 manage.py --init-db
python3 manage.py --host 0.0.0.0 --port 5000 &
BACKEND_PID=$!

cd /app/AccessAppFront
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup INT TERM
wait -n "$BACKEND_PID" "$FRONTEND_PID"
cleanup
