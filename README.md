# Accessibility AI

Accessibility AI is a learning support app with:
- a Flask backend API,
- a Vue frontend,
- a local SQLite database for development.

## Start here (run the app)

If you only need to run the project, use **one command** from the repository root:

```bash
docker compose up --build
```

That command does all of this automatically:
1. Builds the image from the root `Dockerfile`.
2. Starts one container defined in `docker-compose.yml`.
3. Runs the startup command defined directly in `docker-compose.yml`.
4. That command initializes DB, starts backend internally, and starts the Vite frontend server.


Open in your browser:
- **Use this for the app UI:** `http://localhost:5173`

Important:
- The backend API is intentionally not published to your host in Docker Compose.
- Frontend API calls go through the Vite dev server proxy (`/api` -> `127.0.0.1:5000` inside container).
- Docker logs may also show a container IP; still use `localhost:5173` from your host machine.

Optional internal API check (from inside the container):
```bash
docker compose exec app curl -sS http://127.0.0.1:5000/api/v1/health
```

To stop:
- Press `Ctrl + C` in the terminal where Compose is running.

If frontend is not reachable on `http://localhost:5173`, reset containers and volumes once:
```bash
docker compose down -v
docker compose up --build
```

## Windows usage

Use the same command in PowerShell or Command Prompt:

```powershell
docker compose up --build
```

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

## Useful paths

- Backend entrypoint: `AccessBackEnd/manage.py`
- Frontend app root: `AccessAppFront/src/`
- Backend docs index: `AccessBackEnd/docs/README.md`
- AI hardware/runtime planning: `AccessBackEnd/docs/ai_hardware_runtime_guide.md`
- AI pipeline thin contract notes: `AccessBackEnd/docs/ai_pipeline_thin_data_contract.md`
