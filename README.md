# Accessibility AI

Accessibility AI includes a Vue frontend and a Flask backend.

## Repository Structure
- `AccessBackEnd/` — Flask backend.
- `AccessAppFront/` — Vue 3 + Vite frontend.

## Backend (Flask)

### 1) Create and activate virtualenv (do this first)

From repo root:

**macOS/Linux (bash/zsh):**
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r AccessBackEnd/requirements.txt
```

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r AccessBackEnd/requirements.txt
```

> `source .venv/bin/activate` is Unix-only. In PowerShell use `\.venv\Scripts\Activate.ps1`.

### 2) Initialize database schema (required once per local database)

Development DB is persistent and stored at:
- `AccessBackEnd/instance/accessibility_ai.db`

Run **one** of these commands (they depend on current directory):

From repo root:
```bash
python -m flask --app AccessBackEnd.app:create_app init-db
```

From backend directory (**must already be inside `AccessBackEnd/`**):
```bash
cd AccessBackEnd
python -m flask --app app:create_app init-db
```

PowerShell one-liner alternative:
```powershell
cd AccessBackEnd; python -m flask --app app:create_app init-db
```

> `--app app:create_app` only works when your current directory is `AccessBackEnd/`.

### 3) Run backend

Backend runtime entrypoint is **only** `AccessBackEnd/manage.py`.

From repo root:
```bash
python AccessBackEnd/manage.py
```

From backend directory:
```bash
cd AccessBackEnd
python manage.py
```

Default backend URL: `http://localhost:5000`

### Runtime options
```bash
# From repo root
python AccessBackEnd/manage.py --config development
python AccessBackEnd/manage.py --ai-provider live_agent --ai-endpoint http://localhost:8001/ai
python AccessBackEnd/manage.py --init-db
```

### Backend tests
```bash
pytest AccessBackEnd/tests
```

### Backend DB path + init diagnostics
- Flask app-factory DB resolution details and verification query examples live in `AccessBackEnd/docs/README.md`.
- During `init-db`/`--init-db`, the CLI prints the resolved `SQLALCHEMY_DATABASE_URI` so you can confirm the exact SQLite file in use.

## Frontend (Vue + Vite)

### Install dependencies
From repo root:
```bash
npm install --prefix AccessAppFront
```

Or:
```bash
cd AccessAppFront
npm install
```

### Run frontend unit tests
From repo root:
```bash
npm test --prefix AccessAppFront
```

Or inside frontend directory:
```bash
cd AccessAppFront
npm run test
```

### Start frontend dev server
```bash
cd AccessAppFront
npm run dev
```

Default frontend URL: `http://localhost:5173`

## Notes on configuration
- Flask app creation uses `create_app()` in `AccessBackEnd/app/__init__.py`.
- Importing modules does not parse CLI arguments or mutate environment variables.
- Instance overrides can be placed in `AccessBackEnd/instance/config.py`.
- Tests default to in-memory SQLite (`sqlite:///:memory:`), while development defaults to persistent instance SQLite.
