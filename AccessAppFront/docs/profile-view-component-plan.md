# Profile Front-End View Component Plan

## Goal
Build the `/profile` front-end experience by composing Vue components and wiring them to **existing** auth/session data that already lives in stores/APIs, without introducing new store modules or backend routes.

## Scope (current iteration)
- Create/organize profile UI components only.
- Read profile/session fields from existing store state/actions.
- Keep route `/profile` as the entry view.
- No new API endpoints.
- No changes to backend contracts.

## Proposed component breakdown

### 1) `ProfileView.vue` (container/orchestrator)
Responsibilities:
- Gate rendering by auth state (`isAuthenticated`, `sessionChecked`).
- Trigger existing session hydration if needed (`auth.me()` or `initFromSession()`).
- Compose page sections and handle top-level loading/error display.

Expected child components:
- `ProfileHeaderCard.vue` — identity summary (email, role, user id if available).
- `ProfileSessionCard.vue` — session metadata and allowed actions.
- `ProfileSecurityCard.vue` — action area for logout / account actions.
- `ProfileEmptyState.vue` — fallback when user data is missing.

### 2) `ProfileHeaderCard.vue`
Responsibilities:
- Render primary user details from current auth user object.
- Defensive display for missing fields (e.g., unknown role/email placeholders).

Inputs:
- `user` object
- `isAuthenticated` boolean

### 3) `ProfileSessionCard.vue`
Responsibilities:
- Render session details currently available in auth store (`session`, `allowedActions`).
- Show readable list format for allowed actions.

Inputs:
- `session` object
- `allowedActions` array

### 4) `ProfileSecurityCard.vue`
Responsibilities:
- Present action buttons tied to existing flows (logout/navigation).
- Reuse current auth buttons where possible instead of duplicating logic.

Inputs/Emits:
- Emits `logout` and other UI-only events as needed.

### 5) `ProfileEmptyState.vue`
Responsibilities:
- Display recoverable guidance if profile/session data is unavailable.
- Offer retry action that calls existing auth refresh behavior.

## Data wiring plan (no new store/API work)
- Source everything from `useAuthStore()`:
  - `currentUser` / `user`
  - `isAuthenticated`
  - `session`
  - `allowedActions`
  - `authError`
  - `sessionChecked`
- Reuse existing actions:
  - `me()` for session refresh
  - `logout()` for sign-out flow

## Implementation sequence
1. Replace placeholder `ProfileView.vue` with container layout and state gating.
2. Add `components/profile/*` presentational cards.
3. Wire props from auth store into the cards.
4. Connect button events to existing route/logout behavior.
5. Add basic responsive styling consistent with existing card pattern.
6. Run frontend tests/lint and smoke-test `/profile` route.

## Acceptance criteria
- `/profile` renders meaningful user/session information when authenticated.
- No direct API calls from components outside existing store actions.
- No backend or API route changes required.
- Profile button flow still navigates correctly.
- Empty/error/loading states are visible and non-blocking.

## If non-component changes become necessary
If blocked by missing/ambiguous data shape, do **not** immediately add new endpoints.
Instead:
1. Confirm exact payload available from current auth store/session action.
2. Add a tiny adapter/computed mapper in `ProfileView.vue` first.
3. Only if impossible, create a follow-up plan for store-contract changes (separate PR).

## Out of scope for this pass
- Editing backend models/routes.
- Adding profile-edit mutation forms.
- Introducing new global store modules.
