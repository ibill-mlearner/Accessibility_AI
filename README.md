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

Run everything (backend + frontend + DB init) with one command from Windows Command Prompt:

```cmd
scripts\docker\run_all.cmd
```

What this script does automatically:
- detects NVIDIA GPU container runtime availability,
- selects GPU backend when available (CPU fallback otherwise),
- initializes backend DB (`python manage.py --init-db`),
- starts backend + frontend with Docker Compose.

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
- Docker launcher (Windows): `scripts/docker/run_all.cmd`
- GPU runtime probe: `scripts/docker/gpu_runtime_probe.py`
