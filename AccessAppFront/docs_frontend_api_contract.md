# AccessAppFront `/api/v1` Frontend Contract (Short Plan)

## Scope
Standardize frontend resource reads in `AccessAppFront` so bootstrap data is requested from backend v1 endpoints.

## 1) Resource call mapping plan (`src/stores/appStore.js`)
Current bootstrap calls should be migrated to the following targets:

| Current call | Target call |
| --- | --- |
| `/chats` | `/api/v1/chats` |
| `/classes` | `/api/v1/classes` |
| `/notes` | `/api/v1/notes` |
| `/features` | `/api/v1/features` |

## 2) `src/services/api.js` usage notes
- Default base URL is same-origin (`''`) so app requests flow through the frontend host.
- In local dev, Vite proxies `/api` to backend target `http://localhost:5000` by default.
- Runtime override: set `VITE_API_BASE_URL` when targeting a different backend host directly.
- With this setup, the frontend calls `/api/v1/...` paths via the shared axios client without `json-server`.

## 3) UX copy plan (backend-neutral)
Replace mock-specific error wording with backend-neutral language.

- Replace: `Unable to load mock API data. Is json-server running?`
- With: `Unable to load data from the backend service. Please try again.`

## 4) Acceptance criteria
- App bootstrap requests chats, classes, notes, and features from backend `/api/v1` resources.
- Bootstrap behavior has no dependency on `mock-api/db.json`.
- If bootstrap fails, users see backend-neutral error copy.
