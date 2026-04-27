# Accessibility AI

Accessibility AI is a learning support app with:
- a Flask backend API,
- a Vue frontend,
- a local SQLite database for development.

## One-command Windows install script

If you are installing this project on a Windows machine with Docker installed, open PowerShell or Command Prompt in the folder where you want the project to live and run the command block below. It clones the repo into `./Accessibility_AI`, then starts the app with Docker Compose.

Requirements:
- Docker Desktop (or Docker Engine) is installed and running.
- Git is installed and available in your terminal.

### Windows (PowerShell or Command Prompt)

Open PowerShell or Command Prompt in the folder where you want the project, then copy/paste this block:

```bash
git clone --branch main --single-branch https://github.com/ibill-mlearner/Accessibility_AI.git
cd Accessibility_AI
docker compose up --build
```

### Linux

Open a terminal in the folder where you want the project, then run:

```bash
git clone --branch main --single-branch https://github.com/ibill-mlearner/Accessibility_AI.git
cd Accessibility_AI
docker compose up --build
```


## Handoff mode (effective April 25, 2026)

This repository is currently in **handoff cleanup mode** through **April 27, 2026**.

- No new feature development; documentation and cleanup only.
- Single source of truth: `docs/handoff/handoff_master.md` (consolidated steps 1–10).
- Unfinished-work tracker is consolidated in `docs/handoff/handoff_master.md` (Section 11).

## Architecture at a glance

### Backend (Flask)
- API-first service with versioned routes under `/api/v1`.
- SQLAlchemy-backed persistence with local SQLite default for development.
- Authentication/session features plus role-aware route protection.
- Event/logging hooks used to publish operational events for diagnostics and audit evolution.

### Frontend (Vue)
- Vue + Pinia + Vue Router architecture.
- Chat, profile, classes, notes, and accessibility preference views/components.
- API-bound state stores and composables for timeline/chat/session workflows.

### Color accessibility and colorblind support (frontend)

The profile view currently exposes color-vision options (`None`, `Protanopia`, `Deuteranopia`, `Tritanopia`, `Achromatopsia`) as a user preference selector. At this stage, those options are UI-level selections that should be implemented against accessibility standards when mapped to theme tokens and runtime color transforms.

Use the standards below as the source of truth for how colors must function in the app:

- **WCAG 2.2 (W3C Recommendation):** https://www.w3.org/TR/WCAG22/
  - Defines the baseline accessibility conformance model (A / AA / AAA).
- **SC 1.4.1 – Use of Color:** https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
  - Color cannot be the only way information is conveyed.
- **SC 1.4.3 – Contrast (Minimum):** https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
  - Requires minimum contrast for text (commonly 4.5:1 for normal text, 3:1 for large text).
- **SC 1.4.11 – Non-text Contrast:** https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
  - Requires at least 3:1 contrast for essential UI components and visual boundaries.
- **WAI Forms tutorial (don’t rely on color alone):** https://www.w3.org/WAI/tutorials/forms/notifications/
  - Practical implementation examples for validation/error states beyond color-only cues.

Implementation note:
- There is no single official “one-size-fits-all” colorblind palette in WCAG.
- The standardized expectation is: preserve meaning without color-only signals and satisfy required contrast ratios.
- For engineering consistency, define semantic design tokens (success/warning/error/info, interactive states, focus states) and verify each token set against the WCAG criteria above before enabling any colorblind mode in production.

### Typography accessibility and font-family support (frontend)

The profile view also exposes font-family accessibility options (for example: `Default`, `OpenDyslexic`, `Atkinson Hyperlegible`, `Arial`, `Verdana`, `Monospace`). These should be treated as readability accommodations that users can switch at runtime.
Backend startup now synchronizes baseline font-family accommodation records so these profile options can map to persisted database rows consistently across environments.

Use the standards and implementation references below for font/readability behavior:

- **WCAG 2.2 (W3C Recommendation):** https://www.w3.org/TR/WCAG22/
  - Baseline conformance standard for accessible text presentation.
- **SC 1.4.8 – Visual Presentation (AAA):** https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html
  - Readability guidance including line length, spacing, and user control over text presentation.
- **SC 1.4.12 – Text Spacing:** https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html
  - Content must remain functional/understandable when users increase spacing values.
- **SC 1.4.4 – Resize Text:** https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html
  - Text must be resizable without assistive technology and without loss of content/function.
- **WAI Page Structure tutorial:** https://www.w3.org/WAI/tutorials/page-structure/
  - Reinforces semantic structure so font changes do not reduce navigability or comprehension.

Implementation note:
- There is no single WCAG-mandated “one correct font family.”
- The standardized expectation is to allow user adaptation while preserving readability and layout integrity.
- For engineering consistency, map each selectable font option to semantic typography tokens and validate with WCAG criteria for spacing, resize behavior, and overall legibility before production rollout.

### AI integration model
- Runtime provider selection is orchestrated through backend service wiring and config.
- The **AI pipeline “thin contract” module** is treated as an externally shaped integration boundary that this repo consumes and adapts around rather than heavily rewriting internally.
- Current default model behavior remains development-oriented.

## Current status snapshot

### Working/implemented
- End-to-end baseline chat loop is functional.
- DB-backed model catalog and AI interaction route scaffolding exist.
- Single-container Docker dev flow exists.

### In progress / unfinished
- Auth/session hardening and token lifecycle follow-through are still open.
- Full DB-driven runtime model selection still has transitional/static overlap.
- Instructor/admin workflows and accommodations integration still need closure.
- Event logging durability still needs completion beyond current transitional hooks.

### Legacy / transitional areas
- Some implementation notes and TODOs are intentionally left in code/docs while migration from older patterns to module-owned config/services continues.

## Quickstart (current and validated)

### Prerequisites

- Docker Desktop / Docker Engine
- Docker Compose v2
- Git

### Start full stack

```bash
docker compose up --build
```

### Stop stack

```bash
docker compose down
```

### Backend tests

```bash
cd AccessBackEnd
pytest
```

### Frontend unit tests

```bash
cd AccessAppFront
npm test
```

## Useful paths

- Backend entrypoint: `AccessBackEnd/manage.py`
- Frontend app root: `AccessAppFront/src/`
- Backend docs index: `AccessBackEnd/docs/README.md`
- AI hardware/runtime planning: `AccessBackEnd/docs/ai_hardware_runtime_guide.md`
- AI pipeline thin contract notes: `AccessBackEnd/docs/ai_pipeline_thin_data_contract.md`
- Docker startup runner: `scripts/docker/dev_stack_runner.py`
