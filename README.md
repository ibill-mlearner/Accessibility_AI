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
