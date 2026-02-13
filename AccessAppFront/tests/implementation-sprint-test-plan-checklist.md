# Implementation Sprint Test-Planning Checklist

## 1) Unit tests likely impacted by store/action signature changes (`AccessAppFront/tests/unit/`)

### Immediate impact candidates (direct store role/state coupling)
- [ ] `tests/unit/LoginView.spec.js`
  - validates `store.role` changes after login interaction.
  - would break if `login()` action name/signature or side effects change.
- [ ] `tests/unit/LogoutView.spec.js`
  - validates `store.role` reset after logout interaction.
  - would break if `logout()` behavior/signature changes (e.g., additional required args).
- [ ] `tests/unit/ClassesView.spec.js`
  - expects role switching behavior and class filtering via store data.
  - sensitive to `setRole(role)` signature or `roleClasses` getter logic changes.

### Secondary impact candidates (store state shape changes)
- [ ] `tests/unit/HomeView.spec.js`
  - depends on `store.role` to show guest login path.
  - can fail if auth state shape changes (e.g., `role` replaced with `session.userRole`).
- [ ] `tests/unit/SavedNotesView.spec.js`
  - depends on `store.notes` schema and rendering assumptions.
  - can fail if notes move behind selector/getter or schema changes.
- [ ] `tests/unit/AccessibilityView.spec.js`
  - depends on `store.features` schema and availability.
  - can fail if features loading/signature changes.

### Gap to add in this sprint
- [ ] Add dedicated store action tests for `bootstrap()`, `login()`, `logout()`, `setRole(role)` in a new spec (e.g., `tests/unit/appStore.spec.js`) to catch signature changes earlier than view tests.

---

## 2) API-layer mocking strategy at `src/services/api.js` boundary for deterministic store tests

### Test boundary rule
- [ ] Treat `src/services/api.js` as the single network seam.
- [ ] In store tests, mock `../src/services/api` module (not `axios` directly in each test) to avoid transport-level coupling.

### Mock design
- [ ] Use `vi.mock('../../src/services/api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))`.
- [ ] Reset mocks in `beforeEach` with `vi.clearAllMocks()` and recreate deterministic return payloads per case.
- [ ] Return explicit shapes matching app expectations (`{ data: [...] }`, `{ data: {...} }`).
- [ ] Use `mockResolvedValueOnce`/`mockRejectedValueOnce` for sequencing and failure-path precision.

### Determinism and maintainability guardrails
- [ ] Ban test reliance on `json-server` in unit/store tests.
- [ ] Keep fixture builders local to test file or shared helper (e.g., `tests/unit/fixtures/storeFixtures.js`) with stable IDs and timestamps.
- [ ] Assert API call contracts (`toHaveBeenCalledWith('/chats')`, etc.) alongside state assertions.

---

## 3) Planned contract tests

### A. Bootstrap resource loading
- [ ] `bootstrap()` requests `/chats`, `/classes`, `/notes`, `/features` and stores each `data` array.
- [ ] `selectedChatId` is initialized to first chat ID when chats exist.
- [ ] Empty chats array yields `selectedChatId === null`.
- [ ] Any failed bootstrap request sets user-facing error and clears loading state.

### B. CRUD success/error handling
- [ ] For each domain entity (chats/classes/notes/features), add contract tests validating:
  - success path updates state collection deterministically.
  - error path preserves previous stable state and sets actionable error feedback.
- [ ] Validate request shape contracts for create/update/delete endpoints once implemented (path params + payload schema).
- [ ] Verify optimistic updates (if introduced) roll back correctly on API rejection.

### C. Chat interaction sequence orchestration
- [ ] Define and test expected sequence for send-flow orchestration (example):
  1. user draft accepted,
  2. outgoing message staged,
  3. API call issued,
  4. assistant reply appended,
  5. note persistence step (if enabled),
  6. loading/error state finalized.
- [ ] Add order assertions to ensure no out-of-sequence mutation on slow/failing responses.
- [ ] Add concurrency test for rapid sends (ensuring deterministic final transcript ordering policy).

---

## 4) Definition of Done for this sprint

- [ ] Frontend runs against backend endpoints directly (no `json-server` dependency for normal developer flow).
- [ ] Store/integration tests pass using API mocks and/or backend test environment fixtures.
- [ ] Core UX routes remain intact and verifiable:
  - [ ] `/` (home)
  - [ ] `/login`
  - [ ] `/logout`
  - [ ] `/classes/:role`
  - [ ] `/accessibility`
  - [ ] `/saved-notes`
  - [ ] fallback error route behavior
- [ ] Existing core interaction expectations are preserved:
  - [ ] guest vs authenticated behavior
  - [ ] class selection flow
  - [ ] accessibility feature list rendering
  - [ ] saved notes visibility and actions
- [ ] CI includes unit + contract suites and fails on API contract drift.
