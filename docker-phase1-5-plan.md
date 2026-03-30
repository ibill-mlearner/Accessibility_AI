# Docker Phase 1–5 Implementation Notes

## Phase 1: Baseline Inventory

### Existing startup workflow
- Backend starts from `AccessBackEnd/manage.py` on port `5000`.
- Frontend starts with Vite from `AccessAppFront` on port `5173`.
- Backend dependencies are pinned in `AccessBackEnd/requirements.txt` and include `torch`, `transformers`, and `huggingface-hub`.
- Frontend dependencies are managed by npm with scripts for `dev`, `build`, and `preview`.

### Existing runtime assumptions
- Backend CORS default origin is `http://localhost:5173`.
- Backend default database is SQLite in `AccessBackEnd/instance`.
- Frontend API base URL is read from `VITE_API_BASE_URL`.

## Phase 2: Container Strategy

### Service split
- Multi-service approach was selected:
  - `backend` (CPU/default)
  - `backend-gpu` (NVIDIA profile)
  - `frontend` (Vite dev server)

### Image strategy
- Backend uses a dedicated Dockerfile with:
  - `backend-base` target (`python:3.11-slim`) for standard development.
  - `backend-gpu` target (`nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`) for GPU-capable runtime.
- Frontend uses a dedicated Dockerfile with:
  - `frontend-dev` for Vite live development.
  - `frontend-build` and `frontend-prod` for production-ready static serving via nginx.

## Phase 3: Compose + Build Wiring

### Added files
- `.dockerignore`
- `AccessBackEnd/Dockerfile`
- `AccessAppFront/Dockerfile`
- `docker-compose.yml`

### Compose behaviors
- `backend` service:
  - builds `backend-base`
  - uses healthcheck at `/api/v1/health`
  - mounts backend code and persistent instance volume
- `frontend` service:
  - builds `frontend-dev`
  - depends on healthy backend
  - injects `VITE_API_BASE_URL=http://localhost:5000`
- `backend-gpu` service (profile `gpu`):
  - builds `backend-gpu`
  - sets NVIDIA environment variables
  - declares GPU reservation in compose for NVIDIA runtime

## Suggested run commands

### CPU path
```bash
docker compose up --build backend frontend
```

### GPU path (NVIDIA runtime required on host)
```bash
docker compose --profile gpu up --build backend-gpu frontend
```

## Phase 4: Hardware acceleration enablement

### Host prerequisite support
- Added host helper script:
  - `scripts/docker/install_nvidia_toolkit_ubuntu.sh`
- This script configures the NVIDIA container runtime and restarts Docker on Ubuntu hosts.

### In-container accelerator verification
- Added probe script:
  - `scripts/docker/gpu_runtime_probe.py`
- Probe checks:
  - `nvidia-smi` visibility
  - `torch.cuda.is_available()`
- Added compose one-off service:
  - `gpu-runtime-probe` (profile `gpu`)

## Phase 5: Validation and hardening updates

### Hardening applied
- Backend Docker targets now run as a non-root user (`appuser`).
- Frontend dev/build targets run as non-root user (`node`).

### Deployment profile split
- Added explicit compose profiles:
  - `dev` for local backend/frontend
  - `gpu` for accelerator paths and probe
  - `prod` for production-style backend + static frontend

### Operations docs
- Updated root `README.md` with:
  - a single-command Windows launcher: `scripts\docker\run_all.cmd`
  - automatic GPU-runtime detection with CPU fallback
  - automatic database initialization before startup
