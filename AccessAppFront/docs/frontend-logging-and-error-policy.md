# Frontend Logging & Error Policy

This document captures the frontend documentation stream for step 8.

## Logging policy
- Prefer store/composable-managed state over ad-hoc view logging.
- Do not leave unconditional `console.log/info/error` in route views or components.
- If temporary diagnostics are necessary, gate them behind `import.meta.env.DEV` and isolate them in helper functions.
- Keep debug payloads minimal and avoid user-sensitive content.

## Error handling policy
- User-facing errors should be surfaced via store/composable state (`authError`, action status error fields, composable error refs).
- Route views should render existing error state; they should not invent transport-level error parsing inline.
- Retry wording should be consistent and action-oriented (for example: “Please retry”, “Session expired, sign in again”).

## Ownership boundaries
- API transport concerns belong in stores/services/composables, not templates.
- Route guards own navigation-level auth checks (`router.beforeEach` + auth store).
- Components remain primarily presentational; they emit events upward and consume normalized state/props.

## Cleanup status for this step
- Removed stale commented guard code in `src/router.js`.
- Removed development-only `console.info` scaffolding in `SavedNotesView.vue`.
- Removed unused legacy session helper file (`src/stores/helpers/sessionsStuff.js`).
