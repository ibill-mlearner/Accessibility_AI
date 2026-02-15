# Accessibility AI

Accessibility AI includes a Vue frontend and a Flask backend.

## Repository Structure
- `AccessBackEnd/` — Flask backend.
- `AccessAppFront/` — Vue 3 + Vite frontend.

## Backend (Flask)

### 1) Create virtual environment and install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r AccessBackEnd/requirements.txt
```

### 2) Initialize database schema (required once per local database)
The development database is file-backed SQLite and is created under:

- `AccessBackEnd/instance/accessibility_ai.db`

Initialize schema:
```bash
cd AccessBackEnd
flask --app 'app:create_app' init-db
```

### 3) Run backend
From repo root:
```bash
python AccessBackEnd/manage.py
```

Or from backend directory:
```bash
cd AccessBackEnd
python manage.py
```

Default backend URL: `http://localhost:5000`

### Runtime options
```bash
# Select config profile
python AccessBackEnd/manage.py --config development

# Use live AI endpoint (endpoint is required for live_agent)
python AccessBackEnd/manage.py --ai-provider live_agent --ai-endpoint http://localhost:8001/ai

# Initialize DB before server startup
python AccessBackEnd/manage.py --init-db
```

### Backend tests
```bash
pytest AccessBackEnd/tests
```

## Frontend (Vue + Vite)

### Install dependencies
```bash
cd AccessAppFront
npm install
```

### Run frontend unit tests
```bash
npm run test
```

### Start frontend dev server
```bash
npm run dev
```

Default frontend URL: `http://localhost:5173`

## Notes on configuration
- Flask app creation uses `create_app()` in `AccessBackEnd/app/__init__.py`.
- Importing modules does not parse CLI arguments or mutate environment variables.
- Instance overrides can be placed in `AccessBackEnd/instance/config.py`.
- Tests default to in-memory SQLite (`sqlite:///:memory:`), while development defaults to persistent instance SQLite.
