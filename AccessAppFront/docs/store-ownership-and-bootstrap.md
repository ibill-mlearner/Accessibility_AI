# Frontend Store Ownership & Bootstrap Flow

Current store and startup behavior lives under `src/stores`, with network calls using `src/services/api.js`.

## API client base URL
- `src/services/api.js` exports one shared Axios instance named `api`.
- `baseURL` is `import.meta.env.VITE_API_BASE_URL || ''`.
- When `VITE_API_BASE_URL` is set, relative `/api/v1/...` calls go to that backend host.
- When it is empty, requests are same-origin.
- The client does not set `withCredentials`; same-origin browser defaults are used.

## Store ownership
- `authStore`
  - Owns auth/session identity: `role`, `user`, `currentUser`, `isAuthenticated`, `authError`, `session`, `allowedActions`, `sessionChecked`.
  - Actions: `login`, `register`, `me`, `logout`, `initFromSession`, `clearAuthState`, `applyAuthenticatedUser`, `setRole`.
  - `clearAuthState()` also resets chat, class, and feature stores and removes root font styles.
- `chatStore`
  - Owns chat list/selection, model catalog, selected model, optimistic new-chat intent, and chat/message/AI action status.
  - Handles `/api/v1/ai/catalog`, `/api/v1/ai/selection`, chat CRUD, messages, and AI interaction calls.
- `classStore`
  - Owns class list/selection, instructor options, class CRUD, and class action status.
- `featureStore`
  - Owns accessibility feature inventory, selected enabled feature ids, and preference updates/replacement.
- `appBootstrapStore`
  - Owns top-level startup loading state plus aggregate bootstrap `error` and `authError`.

## Startup sequence
- `main.js` creates Pinia, registers it with Vue, instantiates `useAppBootstrapStore(pinia)`, installs the router, and mounts the app.
- `App.vue` `onMounted`:
  1. Calls `auth.me()` if `auth.sessionChecked` is false.
  2. Calls `bootstrap.bootstrap()` only when `auth.isAuthenticated` is true.
- `appBootstrapStore.bootstrap()`:
  1. Sets `loading`, clears bootstrap errors.
  2. Calls `auth.me()` if the session has not been checked.
  3. Stops early when unauthenticated.
  4. For authenticated users, runs these loaders with `Promise.allSettled`:
     - `chatStore.ensureModelCatalogFreshForSession()`
     - `chatStore.fetchChats()`
     - `classStore.fetchClasses()`
     - `featureStore.fetchFeatures()`
  5. If any loader fails with `kind: 'auth'`, sets a session-expired message and calls `auth.logout()`.
  6. If any non-auth typed resource failure occurs, sets a generic bootstrap resource error.
  7. Clears `loading`.

## Session lifecycle details
- `auth.login()` and `auth.register()`:
  - POST credentials/account data.
  - Apply the returned user, reset chat state, refresh session with `me()`, then ensure model selection is ready.
- `auth.me()`:
  - GETs `/api/v1/auth/session`.
  - On success, applies the user, stores session metadata, mirrors `session.allowed_actions`, sets `sessionChecked = true`, and returns `true`.
  - On failure, clears auth and dependent stores, sets `authError`, and returns `false`.
- `auth.logout()`:
  - POSTs `/api/v1/auth/logout` and clears local auth/dependent store state in `finally`.
- `ProfileView` also hydrates chats, classes, and features on direct open when authenticated and those stores are empty.

## Validation commands
- `npm test`
- `npm run build`
- `npm run check`
