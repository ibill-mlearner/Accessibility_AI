# Standalone E2E Smoke Tests (No app code integration required)

This folder contains a standalone Python smoke test that validates the running stack end-to-end as black-box services.

## Why this approach
- Minimal footprint: no Vue/Flask app code changes required.
- No test framework dependency required (stdlib only).
- Useful as a first full-process check before heavier Playwright/Cypress adoption.

## Prerequisites
Start both services in separate terminals from repo root:

1. Backend
```bash
python AccessBackEnd/manage.py --config development
```

2. Frontend
```bash
npm run dev --prefix AccessAppFront
```

## Run
```bash
python e2e_smoke/run_e2e_smoke.py \
  --frontend-base http://127.0.0.1:5173 \
  --backend-base http://127.0.0.1:5000
```

## Result behavior
- The runner executes all 8 checks and does not stop at the first failure.
- A PASS/FAIL line is printed for each step, followed by a final summary.
- Process exit code is `0` only if all 8 checks pass; otherwise `1`.

## What it verifies
1. Frontend root page returns HTML.
2. Backend `/api/v1/health` is up.
3. Register + login round trip using session cookies.
4. Bootstrap resources are reachable:
   - `/api/v1/chats`
   - `/api/v1/classes`
   - `/api/v1/notes`
   - `/api/v1/features`
5. Core data flow works:
   - create class
   - create chat
   - create message
   - create note
   - list chat messages
6. AI interaction endpoint responds (`200` success or `502` upstream provider unavailable).

## Notes
- The script creates a unique test user email each run.
- It is intentionally tolerant of AI provider upstream outages (`502`) while still validating endpoint wiring.

## Troubleshooting connection-refused errors
If you see `WinError 10061` / "actively refused", the smoke runner could not open a TCP connection to one of the configured base URLs.

Common causes:
- Frontend dev server is not started (or started on a different port such as `5174`).
- Backend server is not started.
- Wrong `--frontend-base` or `--backend-base` value.

The runner also auto-detects common frontend mismatches:
- If `127.0.0.1` fails but `localhost` works (or vice versa), it auto-switches and continues.
- If `5173` is closed but `5174`, `4173`, or `3000` is open, it auto-switches and continues.

Examples:
```bash
# If frontend is on a non-default port
python e2e_smoke/run_e2e_smoke.py --frontend-base http://127.0.0.1:5174

# If backend is on a non-default port
python e2e_smoke/run_e2e_smoke.py --backend-base http://127.0.0.1:5001
```
