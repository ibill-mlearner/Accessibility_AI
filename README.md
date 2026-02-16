# Accessibility AI

Accessibility AI includes a Vue frontend and a Flask backend.

## Repository Structure
- `AccessBackEnd/` — Flask backend.
- `AccessAppFront/` — Vue 3 + Vite frontend.

## Backend + Frontend Quick Run (Windows PowerShell)

### Script 1: Full backend setup + run
Run from repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r AccessBackEnd/requirements.txt
python AccessBackEnd/manage.py --init-db
```

Backend URL: `http://localhost:5000`

> On first run, when prompted, enter `y` to load `AccessBackEnd/instance/seed_users.sql`.

### Script 2: Full frontend setup + run
Open a second PowerShell window at repo root:

```powershell
npm install --prefix AccessAppFront
npm run dev --prefix AccessAppFront
```

Frontend URL: `http://localhost:5173`

### Quick nuances
- Backend entrypoint is only `AccessBackEnd/manage.py`.
- Dev DB file is `AccessBackEnd/instance/accessibility_ai.db`.
- Seed data file is `AccessBackEnd/instance/seed_users.sql` (on first run, accept the `--init-db` prompt with `y` to apply it).
- Backend tests: `pytest AccessBackEnd/tests`
- Frontend tests: `npm test --prefix AccessAppFront`
- Optional backend runtime flags:
  - `python AccessBackEnd/manage.py --config development`
  - `python AccessBackEnd/manage.py --ai-provider mock_json`
  - `python AccessBackEnd/manage.py --init-db`

## Planning guardrails
- Chat stabilization scope and entitlement deferral policy: `docs/chat-stabilization-scope.md`.

## Notes on configuration
- Flask app creation uses `create_app()` in `AccessBackEnd/app/__init__.py`.
- Importing modules does not parse CLI arguments or mutate environment variables.
- Instance overrides can be placed in `AccessBackEnd/instance/config.py`.
- Tests default to in-memory SQLite (`sqlite:///:memory:`), while development defaults to persistent instance SQLite.
- AI interaction file logs use `AI_INTERACTION_LOG_DIR` (or `INTERACTION_LOG_DIR`) when set; `DB_LOG_DIRECTORY` is still supported as a deprecated fallback.
- Logging flow details (EventBus observers + AI interaction rotating file logs) are documented in `AccessBackEnd/docs/logging.md`.
