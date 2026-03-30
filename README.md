# Accessibility AI

Accessibility AI is a classroom accessibility assistant app with:
- a Flask backend (`AccessBackEnd/`),
- a Vue 3 frontend (`AccessAppFront/`).

## Quick start (first thing to do)

From the project root folder, run **one command**:

```bash
docker compose up --build
```

If you are on Windows PowerShell, you can run this equivalent helper command:

```powershell
scripts\docker\run_all.cmd
```

After startup:
- frontend: http://localhost:5173
- backend API: http://localhost:5000

## What this command actually does

1. Docker Compose reads `docker-compose.yml`.
2. It builds the single `app` service from the root `Dockerfile`.
3. That service runs `command: ["/usr/local/bin/start_dev_stack.sh"]`.
4. The script:
   - runs `npm ci` (if `node_modules` is missing),
   - runs `python3 manage.py --init-db`,
   - starts backend dev server,
   - starts frontend dev server.

## Notes for this sprint

- This is intentionally a **dev runtime only** setup.
- GPU acceleration is intentionally not part of this setup.
- Production build packaging is intentionally not part of this setup.

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

### AI integration model
- Runtime provider selection is orchestrated through backend service wiring and config.
- The **AI pipeline “thin contract” module** is treated as an externally shaped integration boundary that this repo consumes and adapts around rather than heavily rewriting internally.

## Current status snapshot

### Working/implemented
- End-to-end baseline chat loop is functional.
- DB-backed model catalog and AI interaction route scaffolding exist.

### In progress / unfinished
- Auth/session hardening and token lifecycle follow-through are still open.
- Full DB-driven runtime model selection still has transitional/static overlap.
- Instructor/admin workflows and accommodations integration still need closure.
- Event logging durability still needs completion beyond current transitional hooks.

### Legacy / transitional areas
- Some implementation notes and TODOs are intentionally left in code/docs while migration from older patterns to module-owned config/services continues.

## Current AI model performance expectations

- Default model configuration is optimized for local/dev feasibility first.
- Expect usable but limited quality/latency characteristics versus larger production-focused models.
- Larger model options are possible but require stronger hardware/runtime profiles.

## Useful paths

- Backend entrypoint: `AccessBackEnd/manage.py`
- Frontend app root: `AccessAppFront/src/`
- Backend docs index: `AccessBackEnd/docs/README.md`
- AI hardware/runtime planning: `AccessBackEnd/docs/ai_hardware_runtime_guide.md`
- AI pipeline thin contract notes: `AccessBackEnd/docs/ai_pipeline_thin_data_contract.md`
- Docker startup script: `scripts/docker/start_dev_stack.sh`
