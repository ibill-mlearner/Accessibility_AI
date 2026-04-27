# Frontend Route Guard & Access Policy

This document captures current route-access behavior for frontend handoff workstream step 5.

## Source of truth
- Route definitions and guard logic live in `src/router.js`.
- Auth/session status comes from `useAuthStore()`.

## Current route policy
- Public routes (no auth guard): `/`, `/accessibility`, `/classes`, `/login`, `/logout`, `/error`.
- Protected route: `/profile` (`meta.requiresAuth: true`).
- Catch-all route redirects unknown paths to `/error`.

## Guard behavior (`beforeEach`)
1. If route does **not** require auth, navigation continues.
2. If route requires auth and `auth.sessionChecked` is false, guard runs `auth.me()`.
3. If user is still not authenticated, redirect to `{ name: 'login' }`.
4. Otherwise allow navigation.

## Notes for future hardening
- Expand `meta.requiresAuth` to other routes if product policy requires it.
- Keep guard behavior store-driven (`auth.me()` + `isAuthenticated`) to avoid duplicating auth logic in views.
- Prefer route-meta role checks over ad-hoc component checks if role-level route restrictions are added.
