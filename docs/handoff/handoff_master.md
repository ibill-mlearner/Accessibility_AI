# Accessibility AI Handoff Master Document

**Effective date:**

**Handoff meeting:** April 27, 2026

**Current mode:** hand it off

---

## 1) Scope Freeze and Branch Policy

### Allowed work
- Documentation, runbooks, architecture notes, and onboarding updates.
- Cleanup-only refactors that do not intentionally change runtime behavior.
- Tests for existing behavior.
- CI/configuration clarification and metadata hygiene.
- Low-risk naming/comment improvements.

### Not allowed
- New features or new product surface area.
- Behavior-changing UX flows.
- Schema changes unless required to fix a blocking handoff issue.
- New external service integrations.
- Broad dependency upgrades not required for handoff.

### Branch and PR conventions
- Branch prefixes: `docs/`, `chore/`, `cleanup/`.
- PR title prefixes: `docs:`, `chore:`, `cleanup:`.

### Handoff completion check
1. Scope fits the allowed-work list.
2. No intended behavior change is introduced.
3. Relevant docs are updated.
4. Basic validation commands pass, or limitations are recorded.
5. Checklist status is updated.

---

## 2) Handoff Checklist

| ID | Task | Status | Notes |
|---|---|---|---|
| H1 | Publish scope freeze policy | Done | Section 1. |
| H2 | Confirm branch naming + PR labels in use | Done | Section 1. |
| H3 | Produce architecture one-pager + glossary | Done | Section 3. |
| H4 | Verify README setup commands are current | Done | Section 4. |
| H5 | Publish operational runbook draft | Done | Section 5. |
| H6 | Publish configuration + secrets inventory draft | Done, needs owner follow-up | Section 6; production secret owner/rotation cadence still needs assignment. |
| H7 | Publish backlog + technical debt triage draft | Done, needs owner follow-up | Section 7; owners/ETAs still need assignment. |
| H8 | Publish quality gates + CI audit draft | Done | Section 8. |
| H9 | Capture known risks/open issues for receiving team | Done, active | Sections 7 and 9. |
| H10 | Assemble handoff packet links in one index | Done | Section 9. |
| H11 | Run final handoff meeting and record decisions | Done | Section 10. |

---

## 3) Architecture One-Pager

### System summary
Accessibility AI is a two-tier web app:
- **Frontend:** Vue + Pinia + Vue Router app in `AccessAppFront`.
- **Backend:** Flask API in `AccessBackEnd` with SQLAlchemy and SQLite default storage for local/dev use.

### High-level component map
```text
[Browser / Vue App]
   |
   | HTTP JSON (/api/v1)
   v
[Flask API]
   |
   +--> service layer / AI pipeline gateway
   +--> SQLAlchemy models and repositories
   +--> SQLite local/dev database
```

### Current frontend surface
- App root: `AccessAppFront/src/`.
- Routes: `/`, `/accessibility`, `/classes`, `/login`, `/logout`, `/profile`, `/error`.
- Router protection is metadata-driven: the `/profile` route record currently includes `meta: { requiresAuth: true }`, and `router.beforeEach` checks `to.meta?.requiresAuth` before calling `auth.me()` and redirecting unauthenticated users to `login`.
- Frontend handoff docs:
  - `AccessAppFront/docs/frontend-handoff-snapshot.md`
  - `AccessAppFront/docs/route-guard-access-policy.md`
  - `AccessAppFront/docs/store-ownership-and-bootstrap.md`
  - `AccessAppFront/docs/frontend-logging-and-error-policy.md`

### Current backend surface
- App root: `AccessBackEnd/app/`.
- API routes: `AccessBackEnd/app/api/v1/`.
- Config: `AccessBackEnd/app/config.py`.
- Models: `AccessBackEnd/app/models/`.
- Services and pipeline integration: `AccessBackEnd/app/services/`.
  - Current service files include the AI pipeline gateway, demo/model-download helpers, and the `services/logging/` event/logging modules.
- Database layer: `AccessBackEnd/app/db/`.
  - Current DB files include settings/config helpers, SQLite migrations, model-file loading, prompt-context assembly, and repositories.
- Backend docs index: `AccessBackEnd/docs/README.md`.

### Typical chat request flow
1. User submits a prompt from the frontend chat UI.
2. Frontend store/composable calls the backend `/api/v1` route.
3. Backend validates request/auth context.
4. Backend service layer assembles runtime context and model configuration.
5. AI pipeline/provider gateway returns a normalized response.
6. Backend persists interaction/chat records and returns the response.
7. Frontend updates the chat timeline.

### Glossary
- **Accommodation:** accessibility preference/feature record.
- **Pipeline gateway:** backend boundary that packages provider requests.
- **Thin contract:** constrained AI interaction payload boundary.

---

## 4) Setup Commands Verified

### Docker path
General Docker Desktop path:
```bash
docker compose up --build
```

Explicit project/file path for machines with multiple Docker projects:
```bash
docker compose --project-name accessibility-ai -f docker-compose.yml up --build
```

### Backend local path
```bash
cd AccessBackEnd
python -m venv .venv
# activate .venv for your shell
pip install -r requirements.txt
python manage.py --init-db --host 0.0.0.0 --port 5000
```

### Frontend local path
```bash
cd AccessAppFront
npm ci
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

### Current caveat
- `docker-compose.yml` exposes the Vite frontend on host port `5173`; backend API calls go through the Vite `/api` proxy in the Docker flow.

---

## 5) Operational Runbook

### Start full dev stack with Docker
Requirements: Docker running, repo root checkout.

```bash
docker compose up --build
```

Expected behavior:
- Current dev flow uses one container to start both Flask and Vite through `scripts/docker/dev_stack_runner.py`.
- This runner is for local/dev portability; future deployment work can split frontend and backend into separate containers or hosts.
- Backend listens inside the container on port `5000`.
- Frontend is exposed on host port `5173`.
- Vite proxies `/api` requests to the backend.

Quick checks:
```bash
curl http://localhost:5173/api/v1/health
docker compose logs --tail=200
```

### Stop
```bash
docker compose down
```

### Full Docker reset
```bash
docker compose down -v
```

### Local backend without Docker
```bash
cd AccessBackEnd
python -m venv .venv
# activate .venv for your shell
pip install -r requirements.txt
python manage.py --init-db --host 0.0.0.0 --port 5000
```

### Local frontend without Docker
```bash
cd AccessAppFront
npm ci
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

### Rollback
```bash
git checkout <last-known-good-commit>
docker compose up --build
curl http://localhost:5173/api/v1/health
```

---

## 6) Configuration and Secrets Map

### Key variables

| Variable | Required | Default/example | Secret? |
|---|---|---|---|
| `APP_CONFIG` | No | `development` | No |
| `FLASK_ENV` | No | `development` | No |
| `FLASK_DEBUG` | No | `1` in dev | No |
| `SQLALCHEMY_DATABASE_URI` | Conditionally | SQLite dev path | Potentially |
| `SECRET_KEY` | Yes outside dev | dev fallback exists | Yes |
| `JWT_SECRET_KEY` | Yes outside dev | falls back to `SECRET_KEY` | Yes |
| `CORS_ORIGINS` | No | `http://localhost:5173` | No |
| `AUTH_PROVIDER` | No | `local` | No |
| `AI_PROVIDER` | No | `huggingface` | No |
| `AI_MODEL_NAME` | Conditionally | local/default model setting | No |
| `AI_TIMEOUT_SECONDS` | No | `60` | No |
| `LOG_LEVEL` | No | `INFO`/`DEBUG` | No |
| `STARTUP_TEST_RUNNER_ENABLED` | No | `False` | No |
| `VITE_API_BASE_URL` | No | empty/same-origin | No |
| `VITE_API_PROXY_TARGET` | No | `http://127.0.0.1:5000` | No |

### Secret handling rules
1. Rotate `SECRET_KEY` and `JWT_SECRET_KEY` before non-local deployment.
2. Keep local `.env` files out of source control.
3. Record production secret owner, storage location, and rotation cadence.

---

## 7) Backlog and Technical Debt Triage

### Known open areas
- Instructor/admin workflows exist but need finishing and validation.
- Accessibility/accommodation integration is implemented, but it needs deeper bug-focused testing.
- Event logging needs more thorough failure testing around the current in-process hooks.
- Backend utility cleanup is called out in `AccessBackEnd/docs/engineering_cleanup_report.md`.

### Out of handoff scope
- New feature development.
- Broad dependency upgrades.
- New external integrations.
- University SSO/login integration.
- Production GPU/server-hosted model processing.

---

## 8) Quality Gates and CI Audit

### Current local checks
```bash
cd AccessBackEnd && pytest
cd AccessAppFront && npm test
cd AccessAppFront && npm run build
cd AccessAppFront && npm run check
python scripts/compliance/compliance_gate.py
```

### Current CI state
- `.github/workflows/oss-compliance.yml` automatically runs `python scripts/compliance/compliance_gate.py` on pull requests and pushes to `main`.
- Backend tests, frontend tests, and frontend build checks are documented local/manual gates unless external automation is configured outside this repo.
- Handoff branch note: the frozen branch was split from the `dev 03` work into `main` after validation/testing, then cloned again for this handoff branch.

### Current known check caveats
- Full backend `pytest` needs follow-up: the latest local run failed in existing backend tests and in model-probe cases that attempted blocked Hugging Face network calls.
- Local `python scripts/compliance/compliance_gate.py` can fail when the license lookup for `ai-pipeline-thin` returns `UNKNOWN`; review the generated compliance report before treating this as a release blocker.

### Minimum release/merge gate
1. Backend tests pass.
2. Frontend unit tests pass.
3. Frontend production build passes.
4. Compliance gate passes.
5. Docker startup smoke passes when startup/runtime files change.

### Docker startup smoke
```bash
docker compose up --build
curl http://localhost:5173/api/v1/health
docker compose down
```

---

## 9) Support Transfer Packet

### Packet index
- Architecture summary: section 3.
- Operational runbook: section 5.
- Configuration and secrets map: section 6.
- Backlog and known open areas: section 7.
- Quality gates and CI audit: section 8.
- Final meeting/signoff notes: section 10.
- Frontend current-state docs:
  - `AccessAppFront/docs/frontend-handoff-snapshot.md`
  - `AccessAppFront/docs/route-guard-access-policy.md`
  - `AccessAppFront/docs/store-ownership-and-bootstrap.md`
  - `AccessAppFront/docs/frontend-logging-and-error-policy.md`
- Database layer: `AccessBackEnd/app/db/`.
  - Current DB files include settings/config helpers, SQLite migrations, model-file loading, prompt-context assembly, and repositories.
- Backend docs index: `AccessBackEnd/docs/README.md`.
- Accessibility guide: `docs/accessibility/README.md`.
- Compliance docs:
  - `docs/compliance/oss_mit_readiness.md`
  - `docs/compliance/latest_license_audit.md`
  - `docs/compliance/secret_scan_report.md`

### Transfer status
- [x] MVP app delivered with offered extended support.
- [x] `Professor Tomi Heimonen` has ownership of the frozen branch.
- [x] Final handoff meeting completed.
- [x] Frontend handoff docs reviewed against current frontend code.

### Receiving-team quick checks
```bash
docker compose up --build
curl http://localhost:5173/api/v1/health
cd AccessBackEnd && pytest
cd AccessAppFront && npm run check
python scripts/compliance/compliance_gate.py
```

---

## 10) Final Handoff and Signoff Notes

### Meeting status
- Final handoff meeting occurred on April 27, 2026.
- No additional timeline/demo planning is tracked in this document.

### Decisions/status to carry forward
- Repository remains in stabilization/handoff mode until receiving-team owners accept active maintenance.
- Extended support was offered after MVP delivery.
