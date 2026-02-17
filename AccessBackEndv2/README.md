# AccessBackEndv2

Compact experimental rebuild of the original backend capability set in a compact modular layout.

## Goal
- Keep **full practical API capability** in a tiny footprint.
- Prioritize **make-it-work** behavior over security hardening/config complexity.
- One built-in AI workflow model.

## Run

```bash
pip install -r requirements.txt
python app.py
```

Server: `http://localhost:5055`

Default seeded user:
- email: `demo@access.local`
- password: `demo`

## Included capability areas
- Auth/session: register, login, logout, me, bearer session validation.
- AI workflow: interaction endpoint with persistence.
- Entity/user profile compatibility endpoint.
- Chat management CRUD.
- Message management CRUD + nested chat message routes.
- Class management CRUD.
- Feature management CRUD.
- Note management CRUD.
- Health endpoint.
- Alias endpoints from previous v2 (`/api/login`, `/api/chat`, etc.) kept for compatibility.

## Main endpoints
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/ai/interactions`
- `GET /api/v1/ai/models`
- `GET|POST /api/v1/chats`
- `GET|PUT|PATCH|DELETE /api/v1/chats/<id>`
- `GET|POST /api/v1/messages`
- `GET|PUT|PATCH|DELETE /api/v1/messages/<id>`
- `GET|POST /api/v1/chats/<id>/messages`
- `GET|POST /api/v1/classes`
- `GET|PUT|PATCH|DELETE /api/v1/classes/<id>`
- `GET|POST /api/v1/features`
- `GET|PUT|PATCH|DELETE /api/v1/features/<id>`
- `GET|POST /api/v1/notes`
- `GET|PUT|PATCH|DELETE /api/v1/notes/<id>`
- `GET /api/v1/health`


## File layout
- `app.py` (Flask app bootstrap)
- `routes.py` (all API routing + auth/session middleware)
- `db.py` (SQLite connection + schema/init/seed)
- `ai.py` (single AI workflow model)
- `bootstrap_data.py` (table schema + mirrored seed data bootstrap)


## Prototype full-stack test
```bash
python tests.py
```
This runs backend + Pinia store flow (login -> class/chat/message -> AI interaction).
