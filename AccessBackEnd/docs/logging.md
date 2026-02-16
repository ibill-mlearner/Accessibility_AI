# Backend Logging Overview

This document summarizes how backend logging works in `AccessBackEnd`, including domain event logging, AI interaction file logging, and extension points for adding custom observers/sinks.

## 1) Event logging flow (publisher → `EventBus` → observers)

The backend creates and stores an `EventBus` in Flask `app.extensions` during logging bootstrap.

Flow:

1. **Publisher** creates a `DomainEvent` and publishes it through the shared `EventBus`.
2. **`EventBus`** loops over subscribed observers and invokes `observer.on_event(event)`.
3. **Observers** perform side effects (for example writing to standard logs).

### Current default observer

`initialize_logging()` ensures a `LoggingObserver` is subscribed by default. `LoggingObserver` writes structured event information to the Python logging system (`app.events` logger).

## 2) AI interaction file logging flow (wrapper + rotating writer)

AI interaction logging is implemented with a decorator-style wrapper around the configured AI service:

1. `create_app()` builds the base AI service and stores it in `app.extensions["ai_service"]`.
2. `initialize_logging()` wraps that service with `InteractionLoggingService` (unless already wrapped).
3. `InteractionLoggingService.run_interaction(...)` delegates to the wrapped service and records metadata in a `finally` block (so both success and failure are logged).
4. `RotatingTextLogWriter.append(...)` writes one JSON line per interaction.
5. When the active file reaches `max_lines` (default `2000`), the writer rotates to the next file (`ai_interactions_1.txt`, `ai_interactions_2.txt`, ...).

Logged metadata includes timestamp, caller (`initiated_by`), status, prompt preview, and context payload.

## 3) Config keys

### `LOG_LEVEL`
Controls Python logging level passed to `configure_logging(...)` (for example `DEBUG`, `INFO`, `WARNING`).

### `LOG_JSON`
Configuration flag parsed from env (`true/false` style values). It is available in config and tests, but current bootstrap uses text formatting from `configure_logging(...)`.

### AI interaction log directory key
Preferred key order used by `initialize_logging()`:

1. `AI_INTERACTION_LOG_DIR`
2. `INTERACTION_LOG_DIR` (legacy alias still supported)
3. `DB_LOG_DIRECTORY` (deprecated fallback; warning emitted)
4. Fallback default: `<app.root_path>/instance`

## 4) Where to register additional observers/sinks

### Add domain event observers (EventBus sinks)
Primary registration point: `AccessBackEnd/app/services/logging/bootstrap.py`.

- Extend `DEFAULT_OBSERVER_TYPES` to include your observer class, **or**
- Subscribe custom observers inside `initialize_logging(...)` after `event_bus` initialization.

This keeps observer registration centralized and ensures all app instances get the same baseline observer wiring.

### Add AI interaction sinks/wrappers
Also in `initialize_logging(...)` in `bootstrap.py`.

- Replace/compose `RotatingTextLogWriter` if you need a different sink (e.g., JSONL processor, external collector).
- Replace/compose `InteractionLoggingService` if you need additional metadata or behavior.

Because the service is wired through `app.extensions["ai_service"]`, app startup is the canonical place to swap or chain wrappers.
