# AccessAppFront Quickstart

Frontend handoff summary and local run guide.

## Run locally
```bash
cd AccessAppFront
npm install
npm run dev
```

## Core scripts
- `npm test` — run Vitest unit suite.
- `npm run build` — production bundle via Vite.
- `npm run preview` — serve built output.
- `npm run check` — run unit tests, then build.

## Environment
- `VITE_API_BASE_URL` (optional): backend base URL. Empty uses same-origin calls.

## High-level structure
- `src/views/` route-level pages.
- `src/components/` reusable UI pieces.
- `src/stores/` Pinia state + async actions.
- `src/composables/` chat and UI behavior hooks.
- `src/services/api.js` single Axios boundary.

## Consolidated implementation notes

### Classes view role/capability model
The class views use role-derived capability gates in `ClassesView.vue` and related components.

| Capability | Student | Instructor | Admin |
|---|---:|---:|---:|
| View class list | Yes | Yes | Yes |
| Select active class | Yes | Yes | Yes |
| Edit class details | No | Yes | Yes |
| Create class | No | No | Yes |
| Delete class | No | No | Yes |

Expected wiring:
- `ClassesView.vue` remains the orchestrator.
- `ClassDetailsEditor` handles edit payloads (instructor/admin only).
- `ClassAdminActions` handles create/delete (admin only).
- Store boundary stays in `classStore` (no direct API calls from presentational components).

### Profile view composition model
`/profile` remains a container-led composition that reads existing auth/session data.

Expected sections:
- `ProfileHeaderCard` for identity summary.
- `ProfileSessionCard` for session metadata / allowed actions.
- `ProfileSecurityCard` for logout/security actions.
- `ProfileEmptyState` for missing-data recovery guidance.

Data source remains `useAuthStore()` with existing actions (`me`, `logout`) and state (`user`, `session`, `allowedActions`, `authError`, `sessionChecked`).

## Testing contracts
- Unit tests should mock at `src/services/api.js` or store boundaries, not Axios internals.
- View tests should target stable selectors from child components.
- Login contract: success calls auth login + bootstrap + navigation; failure stays on `/login` and shows auth error.

## Working docs
- `docs/route-guard-access-policy.md`
- `docs/store-ownership-and-bootstrap.md`
- `docs/frontend-logging-and-error-policy.md`
- `docs/frontend-handoff-snapshot.md`
- `tests/implementation-sprint-test-plan-checklist.md`

## Next 10 cleanup steps
1. Validate role gating behavior in `ClassesView` against current auth role payloads.
2. Add/refresh unit tests for class edit/create/delete visibility by role.
3. Confirm profile view data mapping still matches `authStore` response shape.
4. Add/refresh unit tests for profile empty/loading/error states.
5. Remove stale comments that duplicate README guidance.
6. Verify all component-level style imports are still used (no dead CSS modules).
7. Run `npm run check` and capture output in handoff notes.
8. Reconcile any frontend checklist items still marked unknown.
9. Tighten API error messaging consistency surfaced in stores.
10. Publish final frontend handoff signoff in `docs/frontend-handoff-snapshot.md`.
