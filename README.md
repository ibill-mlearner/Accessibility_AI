# Accessibility AI

Accessibility AI includes a Vue frontend and a standalone Flask backend.
The backend is frontend-agnostic and follows an app-factory architecture.

## Repository Structure
- `AccessAppFront/` — Vue 3 + Vite frontend prototype.
- `AccessBackEnd/` — Flask backend (app factory, SQLite, auth, API, observer-based logging).

---

## Frontend (Vue + Vite)

### Stack
- Vue 3 + Vite
- Pinia for state
- Axios for API calls
- `json-server` for local mock endpoints

### Run
From repository root:
```bash
npm install
npm run setup
npm run mock-api
npm run dev
```

Or run directly inside the frontend folder:
```bash
cd AccessAppFront
npm install
npm run mock-api
npm run dev
```

- Mock API runs at `http://localhost:3001`
- Vite app runs at `http://localhost:5173`

### Mock Endpoints
- `GET /chats`
- `GET /features`
- `GET /classes`
- `GET /notes`

---

## Backend (Flask App Factory)

### Architecture Goals
- Standalone backend (frontend-agnostic)
- App-factory pattern (`create_app`)
- SQLite persistence via SQLAlchemy
- Identity management using Flask-Login
- API management with Flask blueprints
- AI component placeholder for this sprint
- Logging decoupled from route handlers and attached as an observer

### Current Backend Components
- **App factory** in `AccessBackEnd/app/__init__.py`
- **Extensions** in `AccessBackEnd/app/extensions.py`:
  - `SQLAlchemy`
  - `Flask-Migrate`
  - `Flask-JWT-Extended`
  - `Flask-CORS`
  - `Flask-Login`
- **API blueprint** in `AccessBackEnd/app/api/v1/routes.py`
  - `GET /api/v1/health`
  - `POST /api/v1/ai/interactions` (returns data from configured AI provider: `mock_json` or `live_agent`)
- **Auth blueprint** in `AccessBackEnd/app/blueprints/auth/routes.py`
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/logout`
- **Observer-style logging** in `AccessBackEnd/app/logging_config.py`
  - Event publishing (`DomainEvent`)
  - Event bus (`EventBus`)
  - Logging observer (`LoggingObserver`)

### Backend Run (local)
From repository root:
```bash
python manage.py
```

Or from the backend folder:
```bash
cd AccessBackEnd
python manage.py
```

Default service URL: `http://localhost:5000`

### Select AI source at startup
You can choose between the mock JSON AI resource and a live AI agent endpoint:

```bash
# Use local mock JSON resource (default)
python manage.py --ai-provider mock_json

# Use a live AI agent endpoint
python manage.py --ai-provider live_agent --ai-endpoint http://localhost:8001/ai
```

You can also choose the app config profile:

```bash
python manage.py --config development --ai-provider mock_json
```

---

## Notes
- The AI endpoint currently supports a configurable mock JSON source and a live endpoint pass-through mode.
- Auth and API layers are designed to evolve independently from the frontend.
