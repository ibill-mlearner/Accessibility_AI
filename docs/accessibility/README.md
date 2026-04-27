# Accessibility Intent Guide

This document explains the **accessibility intent** of the project across frontend UX, backend persistence/API behavior, and AI interaction behavior. It is intentionally more detailed than the root README so contributors can understand *why* the product is structured this way.

> **Current maturity note (discovery-first):**
> This file is currently a discovery marker and reference collection, not a finalized accessibility implementation contract.
> Some standards and references are listed here before full team review; treat them as research inputs and directionally useful targets rather than completed commitments.

## 1) Product-level accessibility intent

Accessibility AI aims to provide:
- adaptable reading and interaction experiences,
- predictable and persistent accommodation preferences,
- and AI responses that respect user and class context constraints.

The core intent is to make accommodations first-class system behavior (not just front-end cosmetics).

## 2) Frontend accessibility intent

### User-facing accommodations
The frontend exposes user preference controls for accommodations including:
- color vision modes,
- readable font-family choices,
- text-size/readability related settings,
- and interaction patterns that should not rely on color-only signals.

### UX behavior expectations
Frontend behavior should:
- preserve meaning without requiring color discrimination,
- maintain usable contrast for text and non-text UI affordances,
- remain navigable and understandable when text spacing/resizing adjustments are applied,
- and keep accommodation controls visible and reversible.

### Standards reference baseline (discovery + target marker)
The project tracks WCAG/WAI guidance below as a standards baseline to review and progressively adopt over time, including:
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- SC 1.4.1 Use of Color: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- SC 1.4.3 Contrast (Minimum): https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- SC 1.4.11 Non-text Contrast: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
- SC 1.4.12 Text Spacing: https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html
- WAI tutorials (forms/page structure):
  - https://www.w3.org/WAI/tutorials/forms/notifications/
  - https://www.w3.org/WAI/tutorials/page-structure/

## 3) Backend accessibility intent

The backend is responsible for turning accommodation choices into durable product behavior:
- persist user accessibility preferences,
- expose those preferences through authenticated APIs,
- and provide a stable contract so frontend controls map to known accommodation records.

Backend intent is to avoid drift between what the UI offers and what the system can persist/apply.

## 4) AI interaction accessibility intent

AI responses should be generated with awareness of:
- user context,
- class/context associations,
- and accommodation-linked system instructions where applicable.

This helps make AI output more usable for different reading and comprehension needs, rather than producing one-size-fits-all responses.

## 5) Practical implementation posture

Contributors should treat accessibility as a cross-layer contract:
- **Frontend**: present and apply accommodations safely.
- **Backend**: persist, validate, and serve accommodations consistently.
- **AI pipeline**: consume accessibility-relevant context in prompt assembly and response behavior.

When implementation tradeoffs appear, prefer decisions that preserve user comprehension, recoverability, and consistency across sessions.

## 6) What this document is (and is not)

This guide currently **is**:
- a central place to gather accessibility references discovered during ongoing handoff/cleanup,
- a directional marker for where implementation rigor should increase,
- and a shared vocabulary for discussing accessibility across frontend/backend/AI workstreams.

This guide currently **is not**:
- a claim of full WCAG conformance,
- a complete engineering checklist with validated pass/fail coverage,
- or a final architecture decision record for every accommodation behavior.
