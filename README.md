# Accessibility AI

Accessibility AI is a learning-support application composed of:
- a Flask backend API (`AccessBackEnd`),
- a Vue + Pinia frontend (`AccessAppFront`),
- and a local SQLite database for development/runtime bootstrapping.

## Quick start (Docker, recommended)

### Requirements

- Docker Desktop (or Docker Engine + Docker Compose v2)
- Git

### Clone + run (Windows, Linux, macOS)

```bash
git clone --branch main --single-branch https://github.com/ibill-mlearner/Accessibility_AI.git
cd Accessibility_AI
docker compose up --build
```

Once containers are ready:
- Frontend: http://localhost:5173
- Backend API health: http://localhost:5000/api/v1/health

Stop services:

```bash
docker compose down
```

## Local development (without Docker)

### Backend

```bash
cd AccessBackEnd
python -m venv .venv
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
python manage.py --init-db --host 0.0.0.0 --port 5000
```

### Frontend

```bash
cd AccessAppFront
npm ci
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

## Handoff mode status

This repository entered **handoff cleanup mode** effective **April 25, 2026**, with planning tracked in `docs/handoff/handoff_master.md`.

- Primary scope during this phase: documentation, stabilization, and cleanup.
- Handoff source-of-truth document: `docs/handoff/handoff_master.md`.

## Architecture at a glance

### Backend (Flask)
- API-first service with versioned routes under `/api/v1`.
- SQLAlchemy-backed persistence with local SQLite default for development.
- Authentication/session features plus role-aware route protection.
- Event/logging hooks used to publish operational events for diagnostics and audit evolution.

### Frontend (Vue)
- Vue + Pinia + Vue Router architecture.
- Chat, profile, classes, notes, and accessibility preference views/components.
- API-bound state stores and composables for timeline/chat/session workflows.

### Accessibility intent (separate guide)

Accessibility intent now lives in a dedicated guide at **`docs/accessibility/README.md`**. That document is intentionally discovery-first right now: it collects references and target-direction notes for frontend accommodations, backend persistence/contracts, and AI interaction behavior before full standards review and formal implementation commitments.

### AI integration model
- Runtime provider selection is orchestrated through backend service wiring and config.
- The **AI pipeline “thin contract” module** is treated as an externally shaped integration boundary that this repo consumes and adapts around rather than heavily rewriting internally.
- Current default model behavior remains development-oriented.

## Current status snapshot

### Working/implemented
- End-to-end baseline chat loop is functional.
- DB-backed model catalog and AI interaction route scaffolding exist.
- Single-container Docker dev flow exists.

### In progress / unfinished
- Auth/session hardening and token lifecycle follow-through are still open.
- Full DB-driven runtime model selection still has transitional/static overlap.
- Instructor/admin workflows and accommodations integration still need closure.
- Event logging durability still needs completion beyond current transitional hooks.

### Legacy / transitional areas
- Some implementation notes and TODOs are intentionally left in code/docs while migration from older patterns to module-owned config/services continues.

## Common commands

```bash
# Start full stack (Docker)
docker compose up --build
# Stop stack
docker compose down
# Backend tests
cd AccessBackEnd && pytest
# Frontend tests
cd AccessAppFront && npm test
```

## Runtime defaults and ports

- Backend Flask API listens on port `5000`.
- Frontend Vite dev server listens on port `5173`.
- Docker startup path runs backend initialization (`--init-db`) before frontend startup.
- Default development DB path is under `AccessBackEnd/instance/` (persistent volume in Docker flow).

## Troubleshooting

- **Port conflict (5000/5173):** stop existing processes or change mapped ports in `docker-compose.yml`.
- **Frontend dependency issues:** run `npm ci` in `AccessAppFront` to match `package-lock.json`.
- **Backend import/dependency issues:** activate backend virtualenv and re-run `pip install -r AccessBackEnd/requirements.txt`.
- **Reset local dev data:** remove `AccessBackEnd/instance/accessibility_ai.db` (non-Docker) or recreate Docker volume.

## Useful paths

- Backend entrypoint: `AccessBackEnd/manage.py`
- Frontend app root: `AccessAppFront/src/`
- Backend docs index: `AccessBackEnd/docs/README.md`
- AI hardware/runtime planning: `AccessBackEnd/docs/ai_hardware_runtime_guide.md`
- AI pipeline thin contract notes: `AccessBackEnd/docs/ai_pipeline_thin_data_contract.md`
- Docker startup runner: `scripts/docker/dev_stack_runner.py`

## License

This repository is licensed under the **MIT License**. See `LICENSE`.

For dependency-level copyleft risk checks, use:

```bash
python scripts/compliance/compliance_gate.py
# optional individual reports
python scripts/compliance/license_audit.py
python scripts/compliance/repo_license_text_scan.py
python scripts/compliance/secret_scan.py
```

Policy and release-gate guidance: `docs/compliance/oss_mit_readiness.md` (including curated dependency mappings in `docs/compliance/python_dependency_licenses.json` and `docs/compliance/first_party_dependency_licenses.json`).
