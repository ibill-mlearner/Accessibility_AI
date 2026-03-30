# Accessibility AI

Accessibility AI is an accessibility-focused learning assistant platform with:
- a **Flask backend** (`AccessBackEnd/`) for auth, API routes, class/notes/chat flows, and model orchestration,
- a **Vue 3 + Vite frontend** (`AccessAppFront/`) for user-facing workflows,
- a modular AI integration path that routes requests through a thin pipeline gateway layer.

## Project purpose

The project focuses on practical classroom accessibility support (accommodations context, role-aware chat, notes, and class-linked workflows) while maintaining clear boundaries between UI, API, DB, and AI runtime concerns.

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
- Current default model behavior remains development-oriented, with GPU acceleration supported through Docker profile/runtime availability.

## Current status snapshot

### Working/implemented
- End-to-end baseline chat loop is functional.
- DB-backed model catalog and AI interaction route scaffolding exist.
- Containerized dev/prod flows exist (CPU + optional GPU path).
- GPU readiness helpers exist (host toolkit installer + runtime probe).

### In progress / unfinished
- Auth/session hardening and token lifecycle follow-through are still open.
- Full DB-driven runtime model selection still has transitional/static overlap.
- Instructor/admin workflows and accommodations integration still need closure.
- Event logging durability still needs completion beyond current transitional hooks.

### Legacy / transitional areas
- Some implementation notes and TODOs are intentionally left in code/docs while migration from older patterns to module-owned config/services continues.

## Docker workflow

The Docker setup is now intentionally minimal: **one root Dockerfile + one compose service** that runs backend and frontend in dev mode.

Run everything with one command:

```bash
docker compose up --build
```

How that command triggers both servers:
- `docker compose` reads `docker-compose.yml` and builds the `app` image using the root `Dockerfile`.
- the compose service explicitly sets `command: ["/usr/local/bin/start_dev_stack.sh"]`.
- that script runs DB init, then starts backend + frontend dev servers in the same container.

What this does:
- starts one container,
- runs `python3 manage.py --init-db`,
- starts backend dev server on `http://localhost:5000`,
- starts frontend dev server on `http://localhost:5173`.

Scope for this sprint:
- no GPU acceleration,
- no production build pipeline,
- no multi-service Docker orchestration.

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
