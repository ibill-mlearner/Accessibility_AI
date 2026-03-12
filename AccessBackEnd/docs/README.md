# Backend Database Initialization Notes

## Default SQLite path resolution for Flask app-factory runs

`create_app()` enables `instance_relative_config=True` and pins `instance_path` to `AccessBackEnd/instance`.
When `SQLALCHEMY_DATABASE_URI` is not explicitly configured, the backend resolves a persistent SQLite database at:

- `AccessBackEnd/instance/accessibility_ai.db`

If you provide a relative SQLite URL (for example `sqlite:///dev.db`), it is resolved relative to Flask's `instance_path`, not the shell working directory. This keeps local DB paths deterministic for both `python -m flask --app ...` and `python manage.py` flows.

## CLI diagnostic for database initialization

The init flows now print the effective URI before creating schema objects:

- Flask CLI: `python -m flask --app AccessBackEnd.app:create_app init-db`
- Runtime CLI: `python AccessBackEnd/manage.py --init-db`

Expected output includes:

```text
Resolved SQLALCHEMY_DATABASE_URI: sqlite:////absolute/path/to/AccessBackEnd/instance/accessibility_ai.db
Database schema initialized.
```

## Quick verification query

After initialization, verify expected tables exist:

```sql
SELECT name FROM sqlite_master
WHERE type = 'table' AND name IN ('users', 'chats')
ORDER BY name;
```

Expected rows include `chats` and `users`.

## Logging

- Logging architecture and extension points are documented in `AccessBackEnd/docs/logging.md`.


## AI model operations

- Hardware/runtime setup and sizing guide: `AccessBackEnd/docs/ai_hardware_runtime_guide.md`.
- System prompt composition workflow: `AccessBackEnd/docs/ai_system_prompt_workflow.md`.
- System prompt step deep-dives: `AccessBackEnd/docs/ai_system_prompt_workflow/` (one file per workflow step).
