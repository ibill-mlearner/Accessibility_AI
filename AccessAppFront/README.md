# AccessAppFront Quickstart

Frontend local run and handoff summary.

## Run locally

    cd AccessAppFront
    npm install
    npm run dev

Frontend default:
- http://localhost:5173

Expected backend API:
- http://localhost:5000

---

## Core scripts

- `npm test` — run Vitest unit tests
- `npm run build` — production build via Vite
- `npm run preview` — preview built frontend
- `npm run check` — run tests and production build together

---

## Environment

Optional environment variables:

- `VITE_API_BASE_URL`
  - Backend API base URL
  - Empty/default uses same-origin API behavior

---

## High-level structure

- `src/views/`
  - Route-level frontend pages

- `src/components/`
  - Reusable UI components

- `src/stores/`
  - Pinia state management and async actions

- `src/composables/`
  - Shared frontend behavior/hooks

- `src/services/api.js`
  - Centralized Axios/API boundary

---

## Role/capability overview

- Students
  - View/select classes

- Instructors
  - Edit class details

- Admins
  - Create/delete classes

Primary orchestration remains in:
- `ClassesView.vue`
- `classStore`
- `useAuthStore()`

---

## Testing notes

- Mock store/API boundaries instead of Axios internals
- Login flow should validate both success and failure paths
- View tests should target stable component selectors

---

## Working docs

- `docs/route-guard-access-policy.md`
- `docs/store-ownership-and-bootstrap.md`
- `docs/frontend-logging-and-error-policy.md`
- `docs/frontend-handoff-snapshot.md`