# Frontend Route Guard & Access Policy

Current route-access behavior is defined in `src/router.js`.

## Route table
- Public routes:
  - `/` -> `HomeView`
  - `/accessibility` -> `AccessibilityView`
  - `/classes` -> `ClassesView`
  - `/login` -> `LoginView`
  - `/logout` -> `LogoutView`
  - `/error` -> `ErrorView`
- Protected route:
  - `/profile` -> `ProfileView`, with route metadata `meta: { requiresAuth: true }`
- Redirects:
  - `/classes/:role` redirects to `/classes`.
  - Unknown paths (`/:pathMatch(.*)*`) redirect to `/error`.

## Guard behavior
`router.beforeEach` only applies auth checks when the destination route metadata exposes `to.meta?.requiresAuth`.

1. If the destination route does not require auth, navigation is allowed.
2. If the destination requires auth, the guard reads `useAuthStore()`.
3. If `auth.sessionChecked` is false, the guard awaits `auth.me()`.
4. If `auth.isAuthenticated` is still false, navigation redirects to `{ name: 'login' }`.
5. Otherwise navigation is allowed.

## Auth source of truth
- The router does not parse tokens, cookies, roles, or permissions directly.
- Session verification is delegated to `auth.me()`, which calls `/api/v1/auth/session` through the shared API client.
- Current route access is authentication-only. Role/capability checks are handled in views/components, not by route meta.

## Practical notes
- Adding route protection means adding `meta: { requiresAuth: true }` to that route record in `src/router.js`.
- Adding role-level route restrictions would require new guard logic; none exists today.
- `/profile` also performs direct-load hydration in `ProfileView`, so the route guard and view both rely on the same auth store state.
