# Frontend Store Ownership & Bootstrap Flow

This document captures store boundaries and startup orchestration for handoff workstream step 6.

## API client base URL (`src/services/api.js`)

- The app uses one shared Axios instance (`api`) for all network calls.
- `baseURL` is read from `VITE_API_BASE_URL`; if set, all relative routes like `/api/v1/chats` resolve against that backend host automatically.
- If `VITE_API_BASE_URL` is empty, requests stay same-origin, which is useful when frontend/backend are served from one domain in development.

## Store ownership map

### `authStore`
- Owns authentication/session identity state (`isAuthenticated`, `role`, `currentUser`, `session`, `allowedActions`, `authError`, `sessionChecked`).
- Owns auth lifecycle actions (`login`, `register`, `me`, `logout`, `clearAuthState`).

### `chatStore`
- Owns chat list/selection, model catalog + selected model, chat action status, message/interaction fetch + mutation methods.

### `classStore`
- Owns class inventory, selected class, instructor options, and class CRUD action status.

### `featureStore`
- Owns accessibility feature inventory, selection, and profile preference mutations.

### `appBootstrapStore`
- Owns application startup orchestration (`bootstrap`) and top-level startup errors.

## Bootstrap sequence (`appBootstrapStore.bootstrap`)
1. Clear bootstrap-local loading/error flags.
2. Ensure auth session is checked (`auth.me()` when needed).
3. Stop early if user is unauthenticated.
4. In parallel (`Promise.allSettled`), load:
   - model catalog freshness (`chatStore.ensureModelCatalogFreshForSession`)
   - chats (`chatStore.fetchChats`)
   - classes (`classStore.fetchClasses`)
   - accessibility features (`featureStore.fetchFeatures`)
5. Convert rejected promises into:
   - `authError` + forced logout for auth failures
   - generic bootstrap `error` for non-auth resource failures

## Ownership rules for maintainers
- Keep network calls inside stores/composables; avoid direct API calls in view templates.
- Keep role/capability derivation in one place per domain (`authStore` + dedicated composables).
- Keep route guard auth checks in router and avoid duplicating route-level auth decisions inside components.
