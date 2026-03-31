# Accessibility AI

Accessibility AI is a learning support app with:
- a Flask backend API,
- a Vue frontend,
- a local SQLite database for development.

## Start here (run the app)

If you pulled new Docker-related changes, always rebuild once before plain `docker compose up`:

```bash
docker compose up --build
```

If you pulled new Docker-related changes, always rebuild once before plain `docker compose up`:

```bash
docker compose up --build
```

After the first successful build, you can restart the existing app container without rebuilding dependencies by running:

```bash
docker compose up
```

That command does all of this automatically:
1. Builds the image from the root `Dockerfile`.
2. Starts one container defined in `docker-compose.yml`.
3. Runs the Docker image default command (`python3 /app/scripts/docker/dev_stack_runner.py`).
4. The Python runner initializes DB, verifies backend health, runs a login smoke check, and then starts backend + frontend dev servers.


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


### Docker reset (short version)

If build context still shows multi-GB transfer after pulling updates, that is usually local files leaking into context (not the number of git commits). This repo now uses a default-deny `.dockerignore` allowlist to avoid that.

If you want a clean seeded DB (for example, to wipe old test chats), reset containers + volumes and start again. This clears the persisted `backend-instance` volume and recreates the app from scratch.

```bash
docker compose down --remove-orphans --volumes
docker compose up --build
```

### Seeded login for local Docker

After startup, sign in with:
- Email: `admin.seed@example.com`
- Password: `Password123!`

Run the containerized login E2E test (requires Docker):

```bash
pytest AccessBackEnd/tests/integration/test_container_login_e2e.py -s
```


## Windows shortcut

If you prefer a Windows command, use:

```cmd
scripts\docker\run_all.cmd
```

This now runs the same single Docker Compose command (`docker compose up --build`) with no GPU prompts and no extra steps.

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
- Docker startup runner: `scripts/docker/dev_stack_runner.py`
