#!/usr/bin/env bash
set -euo pipefail

cd /app/AccessAppFront
if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  npm ci
fi

cd /app/AccessBackEnd
python3 manage.py --init-db
FLASK_DEBUG=0 python3 manage.py --host 127.0.0.1 --port 5000 &
BACKEND_PID=$!

echo "Frontend URL: http://localhost:5173"
echo "Backend API is internal-only in Docker (not published to host)."

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

cd /app/AccessAppFront
exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
