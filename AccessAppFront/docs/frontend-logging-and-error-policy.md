# Frontend Logging & Error Policy

Current guidance for logs and user-facing errors in `AccessAppFront/src`.

## Logging currently in code
- Production-safe debug pattern:
  - `useSendPrompt` logs detailed AI interaction failures only through a helper that returns unless `import.meta.env.DEV` is true.
- Current unconditional log to know about:
  - `AccessibilityView` calls `console.info('[API trigger] updateFeature', ...)` when a user toggles a site-wide accessibility feature.
  - Treat this as the only known non-gated runtime console log in app code.

## Logging policy for changes
- Do not add unconditional `console.log`, `console.info`, `console.warn`, or `console.error` in views/components/composables/stores.
- If diagnostics are needed, gate them behind `import.meta.env.DEV` and keep them in a small helper.
- Do not log prompt text, passwords, session ids, raw user profiles, or full backend payloads unless explicitly scrubbed.
- Prefer store/composable state over logs for expected UI failures.

## User-facing error channels
- `authStore.authError`
  - Login/register/session verification messages.
  - Rendered by `LoginView` and `ProfileView`.
- `appBootstrapStore.error` / `appBootstrapStore.authError`
  - Top-level bootstrap failures.
  - Rendered by `App.vue` as an alert above the routed view.
- Store `actionStatus` maps
  - Per-action loading/error state for chat/class/feature operations.
  - Managed with `setActionStatus` and `setActionError` helpers.
- `useSendPrompt` `interactionError`
  - Chat composer/AI request failures.
  - Normalizes backend/provider error envelopes into user-safe text.
- `useAdminModelDownload`
  - Owns admin model-download status, cancellation, success, and error messages.

## Error-handling boundaries
- `src/services/api.js` only configures the shared Axios client; it does not install interceptors or global error handling.
- Stores/composables own transport calls and normalize errors for UI use.
- Views/components should render existing error state and emit user actions upward.
- Route guards own navigation-level auth checks only.
- Unknown routes use the `/error` view through the router catch-all redirect.

## Current patterns to preserve
- Stores use short, action-oriented messages such as “Unable to load chat messages.”
- Resource bootstrap loaders can throw typed errors from `toResourceError`; bootstrap converts those into aggregate app-level messages.
- `ProfileView` direct-load hydration intentionally catches empty-store fetch failures and relies on store/app error state rather than throwing from the view.
