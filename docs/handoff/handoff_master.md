# Accessibility AI Handoff Master Document (Steps 1–10)

**Effective date:** April 25, 2026  
**Handoff target date:** April 27, 2026  
**Mode:** Cleanup and documentation only

---

## 1) Scope Freeze and Branch Policy

### Purpose
This policy freezes feature development while the team prepares project handoff artifacts. The goal is to stabilize the codebase, reduce risk, and make transition ownership explicit.

### Allowed work
- Documentation updates (README, runbooks, architecture notes, onboarding docs).
- Cleanup-only refactors that **do not** change behavior.
- Tests for existing behavior (no new feature coverage requirements).
- CI/configuration clarification and metadata hygiene.
- Low-risk naming/comment improvements.

### Not allowed
- New features, new product surface area, or behavior-changing UX flows.
- Schema changes unless required to fix a blocking handoff issue.
- New external service integrations.
- Broad dependency upgrades not required for handoff.

### Branch policy
- Treat `main` as stabilization-only.
- Prefer short-lived branches using `docs/`, `chore/`, or `cleanup/` prefixes.
- Merge only after at least one reviewer confirms “no behavior change” (or explicitly records exception).
- PR title guidance: `docs: ...`, `chore: ...`, `cleanup: ...`.


### H2 publish: branch naming + PR labels policy

Use these conventions during handoff freeze to keep changes easy to audit:

- Branch prefixes: `docs/`, `chore/`, `cleanup/`
- PR title prefixes: `docs:`, `chore:`, `cleanup:`
- Suggested PR labels:
  - `handoff`
  - `docs-only`
  - `no-behavior-change`

Examples:
- `docs/handoff-checklist-status`
- `cleanup/remove-print-debugging`
- `chore/logging-comment-clarity`

### Definition of done (handoff mode)
1. Scope aligns with allowed work above.
2. No intended runtime behavior change is introduced.
3. Relevant docs are updated.
4. Basic validation commands pass locally (or known env limitations are recorded).
5. Handoff checklist item is moved to `Done` with owner and timestamp.

### Exception process
1. Mark checklist item as `Blocked` with reason.
2. Create a small exception note in the PR description (why needed, risk, rollback, approver).
3. Obtain explicit maintainer approval before merge.

---

## 2) Handoff Checklist

### Status legend
- `X Done`
- `In Progress`
- `Not Started`

### Checklist (execution)

| ID | Task | Status | Notes |
|---|---|---|---|
| H1 | Publish scope freeze policy | X Done | X policy is in section 1 |
| H2 | Confirm branch naming + PR labels in use | X Done but monitor | X policy published; maintainers should enforce on each new PR |
| H3 | Produce architecture one-pager + glossary | X Done | X in section 3 |
| H4 | Verify README setup commands are current | X Done but monitor | X done in docs, re-verify before final handoff |
| H5 | Publish operational runbook draft | X Done | X included in section 5 |
| H6 | Publish configuration + secrets inventory draft | X Done but unfinished | X draft done; owner/rotation fields still _TBD_ |
| H7 | Publish backlog + technical debt triage draft | X Done but unfinished | X draft done; owners/ETAs not assigned |
| H8 | Publish quality gates + CI audit draft | X Done but unfinished | X audit done; CI workflow/protections still pending |
| H9 | Capture known risks/open issues for receiving team | X Done but active | X tracked in unfinished-work analysis doc (including logger sweep) |
| H10 | Assemble handoff packet links in one index | X Done | X packet index in section 9 |
| H11 | Run final handoff meeting and record decisions | In Progress | X should come back (meeting/signoff not completed yet) |

### Cadence + escalation
- Run regular status sweeps while cleanup is active.
- If any item becomes `Blocked`, escalate to project maintainer.

---

## 3) Architecture One-Pager

### H3 publish artifact
- This section (Section 3) is the one-page architecture reference for handoff.
- Keep this section current when route/module ownership changes.

### System summary
Accessibility AI is a two-tier web application:
- **Frontend:** Vue application (`AccessAppFront`) for chat, profile, classes, notes, and accessibility settings.
- **Backend:** Flask API (`AccessBackEnd`) with SQLAlchemy models and SQLite default storage for development.

### High-level component map
```text
[Browser / Vue App]
   |
   | HTTP (JSON)
   v
[Flask API - /api/v1 routes]
   |
   +--> [Service layer / pipeline gateway]
   +--> [DB repositories / SQLAlchemy models]
   +--> [SQLite DB (dev default)]
```

### Request/data flow (typical chat)
1. User submits prompt in frontend chat UI.
2. Frontend store/composable sends API request to backend route.
3. Backend validates request schema and route authorization context.
4. Backend service layer assembles runtime context + model configuration.
5. AI pipeline/provider call is made through gateway abstractions.
6. Response is normalized and persisted as interaction/chat records.
7. Backend returns payload; frontend updates timeline state.

### Core modules
- Frontend app root: `AccessAppFront/src/`.
- Backend app root: `AccessBackEnd/app/`.
- API routes: `app/api/v1/`.
- DB/settings: `app/db/`.
- Models: `app/models/`.
- Services/pipeline: `app/services/`.

### Runtime + dependencies
- Local dev default: docker compose / local Python + Node workflows.
- DB default: SQLite under `AccessBackEnd/instance/`.
- Key stacks: Flask/SQLAlchemy and Vue/Pinia/Vue Router/Vite.

### Glossary
- **Accommodation:** user-selectable accessibility preference.
- **Pipeline gateway:** backend abstraction layer that packages/selects provider requests.
- **Thin contract:** constrained interface boundary for model interaction payloads.
- **Module config:** config object owned by a specific subsystem.
- **Handoff packet:** full documentation set transferred to receiving team.

---

## 5) Operational Runbooks

### Start / deploy (development stack)
Preconditions: Docker running, ports 5173/5000 available, repo root checkout.

```bash
docker compose up --build
```

Expected behavior:
- Backend starts via `AccessBackEnd/manage.py --init-db --host 0.0.0.0 --port 5000`.
- Health endpoint available at `/api/v1/health`.
- Frontend server starts on `5173`.

Verification:
```bash
curl -s http://localhost:5000/api/v1/health
```

### Stop
```bash
docker compose down
```

Optional clean reset:
```bash
docker compose down -v
```

### Rollback (code/config)
1. Identify last known good commit/tag.
2. Revert offending commit(s) or checkout known-good revision.
3. Rebuild stack (`docker compose up --build`).
4. Validate health and login smoke path.
5. Record incident note (what/why/owner/next step).

### Incident triage
Severity:
- SEV-1: service unavailable.
- SEV-2: core flow degraded.
- SEV-3: non-blocking docs/config issue.

First 15 minutes:
1. Confirm blast radius.
2. Check logs: `docker compose logs --tail=200 app`.
3. Check health endpoint.
4. If auth issue suspected, verify `/api/v1/auth/login` seed-login path.
5. Decide fix-forward vs rollback.

Escalate unresolved SEV-2 or any SEV-1 after 30 minutes.

---

## 6) Configuration and Secrets Map

### Storage model
- Local dev: shell env vars or compose environment block.
- Non-local: use secret manager; do not hardcode secrets.

### Config inventory (key vars)

| Variable | Required | Default/Example | Secret? |
|---|---|---|---|
| `APP_CONFIG` | No | `development` | No |
| `FLASK_ENV` | No | `development` | No |
| `FLASK_DEBUG` | No | `1` (dev) | No |
| `SQLALCHEMY_DATABASE_URI` | Conditionally required | `sqlite:////app/AccessBackEnd/instance/accessibility_ai.db` | Potentially |
| `SECRET_KEY` | Yes (non-dev) | dev default present | Yes |
| `JWT_SECRET_KEY` | Yes (non-dev) | falls back to `SECRET_KEY` | Yes |
| `CORS_ORIGINS` | No | `http://localhost:5173` | No |
| `AUTH_PROVIDER` | No | `local` | No |
| `AI_PROVIDER` | No | `huggingface` | No |
| `AI_MODEL_NAME` | Conditionally required | local model path default | No |
| `AI_TIMEOUT_SECONDS` | No | `60` | No |
| `LOG_LEVEL` | No | `INFO`/`DEBUG` | No |
| `STARTUP_TEST_RUNNER_ENABLED` | No | `False` | No |
| `VITE_API_BASE_URL` | No | empty (same-origin) | No |

### Secret handling rules
1. Rotate `SECRET_KEY` and `JWT_SECRET_KEY` before non-local deployment handoff.
2. Never commit plaintext secrets.
3. Keep local `.env` files excluded from source control.
4. Record production secret storage location and rotation cadence.

---

## 7) Backlog and Technical Debt Triage

### Must-fix before handoff
- M1: Confirm handoff docs are internally consistent and linked.
- M2: Fill owner/contact placeholders across artifacts.
- M3: Verify startup + health path from clean checkout.

### Post-handoff priorities
- P1: Auth/session hardening and token lifecycle completion.
- P2: Full DB-driven runtime model selection completion.
- P3: Instructor/admin workflow closure.
- P4: Event logging durability hardening.
- P5: CI formalization and branch protections.

### Won't do in handoff window
- W1: New feature development.
- W2: Broad dependency upgrades.
- W3: New external integrations.

Recommended first sprint:
1. Resolve M* items.
2. Prioritize P1 and P5.
3. Assign ownership/SLAs for operations and secrets rotation.

---

## 8) Quality Gates and CI Audit

### Current observed checks
- Backend tests via `cd AccessBackEnd && pytest`.
- Frontend unit tests via `cd AccessAppFront && npm test`.
- Frontend build validation via `cd AccessAppFront && npm run build`.
- Container startup contract tests exist in backend utility tests.

### CI state
- No repository-level `.github/workflows/*.yml` CI workflow file is present in the tree.
- Current quality checks appear manual/local (or external undocumented automation).

### Minimum gate policy (recommended)
1. Backend tests.
2. Frontend unit tests.
3. Frontend build check.
4. Container startup smoke when startup/runtime changes:
   - `docker compose up --build`
   - `curl -s http://localhost:5000/api/v1/health`
   - `docker compose down`

Branch protection recommendation:
- Require PR review approval.
- Require passing backend + frontend checks.
- Block force-push to protected default branch.

---

## 9) Support Transfer Packet

### Required packet contents
- Scope/branch policy (this document section 1).
- Consolidated unfinished-work tracker (section 11).
- Checklist/owner matrix (section 2).
- Architecture summary (section 3).
- Operational runbooks (section 5).
- Config + secrets map (section 6).
- Backlog/triage (section 7).
- Quality gates/CI audit (section 8).
- Final handoff meeting and signoff (section 10).

### Top 10 things receiving team should know
1. Project is in cleanup/documentation handoff mode for April 25–27, 2026.
2. Feature development is intentionally paused during this window.
3. Startup baseline uses Docker Compose from repo root.
4. Backend health endpoint is `/api/v1/health`.
5. Local stack uses seeded-data assumptions for smoke login validation.
6. Ownership placeholders still must be assigned before signoff.
7. Auth/session hardening remains a post-handoff high-priority item.
8. Runtime model selection has transitional overlap requiring follow-up.
9. No repository-native CI workflow file currently exists in tree.
10. This master document is the source of truth for transition operations.

### Delivery checklist
- [ ] All sections validated and accurate.
- [ ] `_TBD_` owners replaced with names.
- [ ] Contacts/escalations complete.
- [ ] Secrets location/rotation documented.
- [ ] Receiving team confirms readability and access.

---

## 10) Final Handoff Meeting and Signoff

### Meeting details
- Target date: **April 27, 2026**
- Duration: 60–90 minutes
- Facilitator: _TBD_
- Recorder: _TBD_
- Attendees: _TBD_

### Agenda
1. Scope boundaries recap.
2. Architecture walkthrough.
3. Runbooks walkthrough.
4. Configuration + secrets review.
5. Backlog/risk review (M*/P*/W*).
6. Quality gates/CI posture review.
7. Ownership assignment confirmation.
8. Open Q&A and blocker list.
9. Acceptance decision and next-steps schedule.

### Pre-meeting requirements
- All handoff content shared with attendees.
- Owners/backups assigned in matrix.
- Known blockers listed with status.
- Recording destination/access prepared.

### Decision log

| Topic | Decision | Owner | Date (UTC) |
|---|---|---|---|
| Scope freeze acceptance | _TBD_ | _TBD_ | _TBD_ |
| Operations ownership | _TBD_ | _TBD_ | _TBD_ |
| Secrets ownership and rotation cadence | _TBD_ | _TBD_ | _TBD_ |
| Sprint-1 priorities after handoff | _TBD_ | _TBD_ | _TBD_ |

### Signoff table

| Team | Representative | Accepted? (Y/N) | Date (UTC) | Notes |
|---|---|---|---|---|
| Current/transferring team | _TBD_ | _TBD_ | _TBD_ | |
| Receiving/maintaining team | _TBD_ | _TBD_ | _TBD_ | |
| Product/leadership (if required) | _TBD_ | _TBD_ | _TBD_ | |

### Post-meeting actions
- Publish meeting notes and recording link.
- Update checklist statuses.
- Create first post-handoff sprint board from P* priorities.
- Confirm escalation/on-call ownership.

### Completion criteria
Handoff is complete when:
1. Receiving team has explicitly accepted signoff.
2. Named owners exist for operations, secrets, and backlog.
3. Sections are accessible and validated.
4. First post-handoff sprint priorities are scheduled.


## 11) Consolidated Unfinished Work Tracker

This section consolidates the unfinished-work analysis that was previously maintained in a separate planning document.

### API items
- Admin model download endpoint still uses transitional success semantics; finalize lifecycle states (`queued`, `in_progress`, `completed`, `failed`).
- AI model catalog still exposes migration compatibility aliases and legacy fields; publish deprecation schedule and remove aliases after checkpoint.
- `reconcile` query parameter on `/api/v1/ai/models` remains a no-op; remove or implement behavior.
- Auth registration still uses transitional security stamp pattern; finalize generation/rotation policy.

### Logging / event bus items
- Event bus is process-local and synchronous; decide whether durable sink is required for handoff-critical telemetry.
- Add observer-failure isolation policy and tests for event publish fanout.
- Add explicit event catalog/versioning guidance and correlation-ID conventions.

### Database items
- `create_standalone_db(...)` control-flow risk when `create_schema=False`; stabilize return path.
- SQLite migration path remains additive/best-effort; harden migration ownership and ordering.
- AI model inventory duplicate-insert edge case remains unresolved (`xfail`); close prior to production migration.
- SQLite URL normalization TODO remains open in settings layer.

### Utilities / contract items
- `app/utils/api_checker/operations.py` remains broad and tightly coupled to Flask globals.
- `app/utils/api_checker/validator.py` still mixes canonical/legacy alias behavior.
- `app/utils/env_config.py` naming/validation mismatches remain unresolved.
- `app/utils/api_checker/mutations.py` is an empty placeholder; remove or implement.

### Suggested next-steps order
1. Observability + API contract cleanup (`print` remnants, no-op parameters, response lifecycle semantics).
2. DB stability fixes (standalone DB control flow and AI inventory dedup).
3. Utility module decomposition with explicit ownership boundaries.
4. Regression checkpoint (`pytest tests/api -q`, `pytest tests/db -q`, targeted AI-resolution tests).
