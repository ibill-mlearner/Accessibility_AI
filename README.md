# Accessibility AI

Accessibility AI is a local-development project with:
- **Flask backend** (`AccessBackEnd/`)
- **Vue 3 + Vite frontend** (`AccessAppFront/`)

---

## Fastest install + run (Windows PowerShell)

### 1) Start backend
From repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r AccessBackEnd/requirements.txt
python AccessBackEnd/manage.py --init-db
```

When prompted during `--init-db`, enter `y` to apply baseline seed data.

After the seed completes, stop that backend process (`Ctrl+C`) and restart without DB init:

```powershell
python AccessBackEnd/manage.py
```

Backend runs at: `http://localhost:5000`

### 2) Start frontend
Open a second PowerShell window at repo root:

```powershell
npm install --prefix AccessAppFront
npm run dev --prefix AccessAppFront
```

Frontend runs at: `http://localhost:5173`

That is the complete local startup path.

---

## Fastest install + run (macOS/Linux Bash)

### 1) Start backend
From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r AccessBackEnd/requirements.txt
python AccessBackEnd/manage.py --init-db
```

When prompted during `--init-db`, enter `y` to apply baseline seed data.

After the seed completes, stop that backend process (`Ctrl+C`) and restart without DB init:

```bash
python AccessBackEnd/manage.py
```

Backend runs at: `http://localhost:5000`

### 2) Start frontend
Open a second terminal window at repo root:

```bash
npm install --prefix AccessAppFront
npm run dev --prefix AccessAppFront
```

Frontend runs at: `http://localhost:5173`

That is the complete local startup path for Bash-based environments.

---

## Docker Quickstart

This repository includes Docker automation for deployment and local orchestration only; API routes and app behavior are unchanged.

### Prerequisites

- Docker
- Docker Compose plugin (`docker compose`)
- *(Optional for GPU passthrough)* NVIDIA Container Toolkit on NVIDIA hosts

### Start the stack

From repo root, run one of:

```bash
docker compose up --build
```

or (if using the included `Makefile`):

```bash
make up
```

### Default URLs

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:5000`

### Compose environment variables

- `SECRET_KEY` *(recommended for non-dev use)*
- `JWT_SECRET_KEY` *(recommended for non-dev use)*
- `CORS_ORIGINS` *(used by backend CORS config in compose)*
- `VITE_API_BASE_URL` *(frontend build arg for API base URL)*

### Logs, shutdown, and reset

```bash
docker compose logs -f
docker compose down
docker compose down -v
```

`docker compose down -v` removes project-local Docker volumes (including persisted backend instance volume data).

If using `Makefile` shortcuts:

```bash
make logs
make down
make reset
```

### Quick verification

- Backend health endpoint:

```bash
curl http://localhost:5000/api/v1/health
```

- Frontend load check: open `http://localhost:8080` in a browser.

### GPU passthrough notes

- The compose backend service is configured with `gpus: all` and NVIDIA runtime environment variables so GPU-capable hosts expose all available devices to the container automatically.
- On hosts without GPU support configured in Docker, remove/comment the `gpus: all` line in `docker-compose.yml` to run CPU-only.
- Optional GPU visibility check (inside backend container):

```bash
docker compose exec backend sh -lc 'ls /dev | grep -E "nvidia|dri" || true; command -v nvidia-smi >/dev/null && nvidia-smi || true'
```

---

## QOL and QA issues (still unfinished / known issues)

1. **Auth token lifecycle hardening is incomplete.**  
   There is an explicit TODO for stronger token time-limit enforcement.

2. **Model selection is still partially static in config.**  
   There is an explicit TODO to fully move runtime model selection to DB-backed `ai_models` instead of static config defaults.

3. **Core chat loop is working, but stabilization follow-through is still incomplete.**  
   Chat back-and-forth is functional now, but auth-path validation and final API contract hardening still need to be fully closed out.

4. **Current defaults are optimized for local dev, not production performance.**  
   HTTP and other development-first defaults were kept to prioritize minimum working chat functionality, so production hardening is still required.

5. **Frontend session hydration is creating an avoidable security gap and should be removed.**  
   The frontend currently restores `role/currentUser/isAuthenticated` from `sessionStorage` before backend verification, so client state can temporarily diverge from server auth truth; session state should be derived from backend-authenticated responses only.

6. **GPU runtime/hardware selection is not implemented yet.**  
   Model execution is still effectively CPU-oriented in current defaults, so GPU selection/acceleration support remains a pending item.

---

## Feature requirements still unfinished

- **Accommodations via system prompts** (implementation + chat integration).
- **Instructor classes** (complete end-to-end workflow).
- **Admin controls** (role-safe management and hardening).
- **User notes** (complete feature flow and integration).
- **Real event logging** (replace EventBus-style logging with durable audit logs).

---

## What needs to be done next

1. **Keep the working chat loop stable while finalizing auth-path validation and contract cleanup.**
2. **Remove frontend session hydration and make backend auth the single source of truth** for role/user/session state across bootstrap and login flows (includes token/session hardening work).
3. **Complete DB-driven AI model/runtime selection** so different models can be selected at runtime instead of staying pinned to static defaults.
4. **Create a production readiness pass** (move from HTTP-first local defaults, enforce secure cookie/transport settings, and finalize deploy-specific config).
5. **Add GPU runtime/hardware selection support** so model execution can use accelerator-backed profiles when available.

---

## Current AI model performance expectations

- Default model is **`Qwen/Qwen2.5-0.5B-Instruct`**, chosen as a **small CPU-friendly baseline** for local machines while GPU selection remains unimplemented.
- Expect **functional but limited quality** versus larger models (weaker reasoning depth, shorter effective context behavior, more output variability).
- Larger model options exist, but typically trade speed and memory for quality.
- Current setup should be treated as **development-grade inference behavior**, not production-grade latency/quality guarantees.

---

## Useful paths

- Backend entrypoint: `AccessBackEnd/manage.py`
- Dev database: `AccessBackEnd/instance/accessibility_ai.db`
- Seed SQL files: `AccessBackEnd/instance/seed_*.sql`
- Chat scope guardrails: `docs/chat-stabilization-scope.md`
