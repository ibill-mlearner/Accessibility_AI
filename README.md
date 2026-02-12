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

### Current Status
- The backend is actively used by the frontend contract layer and exposes stable v1 endpoints.
- API resources (`chats`, `messages`, `classes`, `notes`, `features`) currently use in-memory pass-through storage for endpoint validation and integration work.
- Authentication (register/login/logout) is implemented with persisted users in SQLite.
- **Important:** the full AI pipeline (prompt orchestration, RAG flow, policy routing, etc.) is **not implemented yet**. The current AI service is a lightweight gateway that returns mock JSON or forwards a prompt to a configured live endpoint.

### Backend Architecture
- **App factory**: `create_app()` in `AccessBackEnd/app/__init__.py`
- **Config profiles**: development, testing, production (`AccessBackEnd/app/config.py`)
- **Extensions** (`AccessBackEnd/app/extensions.py`):
  - `SQLAlchemy`
  - `Flask-Migrate`
  - `Flask-JWT-Extended`
  - `Flask-CORS`
  - `Flask-Login`
- **Event-driven logging** (`AccessBackEnd/app/logging_config.py`):
  - `DomainEvent` + `EventBus`
  - `LoggingObserver` subscriber
- **AI gateway service** (`AccessBackEnd/app/services/ai_pipeline_service.py`):
  - `mock_json` provider reads `app/resources/mock_ai_response.json`
  - `live_agent` provider forwards prompt payload to an external HTTP endpoint

### Implemented API Endpoints
Base API prefix: `/api/v1`

- `GET /api/v1/health`
- `POST /api/v1/ai/interactions`
- `GET /api/v1/api_view` (built-in HTML tester for v1 routes)
- Resource CRUD:
  - `GET, POST /api/v1/chats`
  - `GET, PUT, PATCH, DELETE /api/v1/chats/<id>`
  - `GET, POST /api/v1/messages`
  - `GET, PUT, PATCH, DELETE /api/v1/messages/<id>`
  - `GET, POST /api/v1/classes`
  - `GET, PUT, PATCH, DELETE /api/v1/classes/<id>`
  - `GET, POST /api/v1/notes`
  - `GET, PUT, PATCH, DELETE /api/v1/notes/<id>`
  - `GET, POST /api/v1/features`
  - `GET, PUT, PATCH, DELETE /api/v1/features/<id>`

Auth prefix: `/auth`

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`

### Run Backend Locally
Install dependencies:
```bash
python -m pip install -r AccessBackEnd/requirements.txt
```

Run from repository root:
```bash
python AccessBackEnd/manage.py
```

Or run inside backend folder:
```bash
cd AccessBackEnd
python -m pip install -r requirements.txt
python manage.py
```

Default URL: `http://localhost:5000`

### Runtime Options
Choose config profile and AI gateway mode at startup:

```bash
# Default mock provider
python AccessBackEnd/manage.py --config development --ai-provider mock_json

# Forward interactions to a live endpoint
python AccessBackEnd/manage.py --ai-provider live_agent --ai-endpoint http://localhost:8001/ai

# Custom bind
python AccessBackEnd/manage.py --host 0.0.0.0 --port 5000
```

### AI Behavior Right Now (Pre-Pipeline)
`POST /api/v1/ai/interactions` currently accepts a JSON payload and reads `prompt` for processing.

- `system_prompt` and `rag` keys are accepted for forward compatibility, but are not yet executed through a real pipeline.
- Response shaping is intentionally minimal while backend contracts are being finalized.
- Once the AI pipeline is implemented, this endpoint will route through multi-step processing instead of direct provider pass-through.

---

## Notes
- The AI endpoint currently supports a configurable mock JSON source and a live endpoint pass-through mode.
- Auth and API layers are designed to evolve independently from the frontend.
