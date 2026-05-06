# Frontend Handoff Snapshot

Concise current-state snapshot for handoff review.

## Implemented app surface
- Vue 3 + Pinia + Vue Router + Axios frontend under `AccessAppFront/src`.
- Routes currently implemented:
  - `/`, `/accessibility`, `/classes`, `/login`, `/logout`, `/profile`, `/error`.
  - `/profile` is the only route record with `meta: { requiresAuth: true }`; the guard checks `to.meta?.requiresAuth`.
  - `/classes/:role` redirects to `/classes`; unknown paths redirect to `/error`.
- `App.vue` owns the shared shell, bootstrap alert rendering, and root accessibility presentation styles.
- `HomeView` owns the chat timeline/composer flow through composables.
- `AccessibilityView` owns site-wide feature toggles.
- `ClassesView` owns class selection/editing UI.
- `ProfileView` owns account/session display, profile preferences, and admin-only model/class actions.

## State and services
- `src/services/api.js` exports one Axios client with `baseURL` from `VITE_API_BASE_URL` or same-origin fallback.
- `authStore` owns auth/session identity and resets dependent stores on auth clear/logout.
- `appBootstrapStore` verifies session and loads model catalog, chats, classes, and features for authenticated users.
- `chatStore`, `classStore`, and `featureStore` own their domain data plus per-action loading/error maps.
- Shared helpers normalize action status, selection fallback, and typed resource errors.

## Current error/logging behavior
- User-facing errors are surfaced through store/composable state, then rendered by views/components.
- `useSendPrompt` gates detailed AI failure logging behind `import.meta.env.DEV`.
- Known non-gated app log: `AccessibilityView` logs feature-toggle intent with `console.info`.
- No global Axios interceptor or global Vue error handler is configured.

## Current automated coverage
Unit specs currently exist for:
- `LoginView`
- `SidebarNav`
- `HeaderBar`
- `ComposerBar`
- `ProfileAdminModelDownloadCard`
- `authStore`
- `chatStore` model selection behavior

## Validation commands
- `npm test` runs the Vitest unit suite.
- `npm run build` runs the production Vite build.
- `npm run check` runs tests and then the production build.

## Remaining gaps visible from current code/tests
- Route guard behavior is documented but does not have a dedicated router spec in the current unit suite.
- Several leaf components and composables are still covered indirectly rather than by focused unit specs.
- Logging policy has one current exception: the unconditional feature-toggle `console.info` in `AccessibilityView`.
