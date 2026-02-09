# Accessibility AI Frontend (Vue + Vite)

Prototype UI based on the provided wireframes.

## Stack
- Vue 3 + Vite
- Pinia for state
- Axios for API calls
- json-server for mock endpoints

## Run
```bash
npm install
npm run mock-api
npm run dev
```

`json-server` runs at `http://localhost:3001` and Vite runs at `http://localhost:5173`.

## API endpoints (mock)
- `GET /chats`
- `GET /features`
- `GET /classes`
- `GET /notes`

Authentication is mocked in the UI; real auth is expected from Flask Identity later.
