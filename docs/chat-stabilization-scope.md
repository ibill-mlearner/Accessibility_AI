# Chat Stabilization Scope Guardrails

## Phase rule: entitlement work is out-of-scope
For the current chat stabilization phase, user-feature entitlement implementation is **explicitly out-of-scope**.

This means the team should prioritize stabilizing canonical chat behavior and avoid introducing new entitlement architecture until chat is stable.

## Model freeze during chat stabilization
Keep the existing `features` and `accommodations` models unchanged during this phase, unless a direct chat bug requires a minimal targeted fix.

## Explicit exclusions for this phase
Do **not** add any of the following while chat stabilization is in progress:
- new entitlement tables
- entitlement grant services
- feature-access policy logic

## Backlog ticket: resume entitlement design after chat stabilization

- **Ticket ID:** `BACKLOG-CHAT-ENTITLEMENTS-01`
- **Title:** Resume user-feature entitlement design after chat stabilization
- **Status:** Backlog (blocked)
- **When to start:** only after chat stabilization exit criteria are met

### Prerequisites
1. canonical chat flow is passing
2. chat authorization paths are validated
3. API contracts for chat are locked

### Deliverables (future phase)
- entitlement data model proposal and migration plan
- grant/revocation service design
- chat feature-access policy integration plan
- rollout and compatibility checklist

## PR merge gate for stabilization window
If any pull request touches entitlement-related files during chat stabilization, a **scope review is required before merge**.

### Scope-review checklist
- Does the change directly fix a chat-stability bug?
- Is the change the smallest possible surface area?
- Does it avoid introducing new entitlement architecture?
- Is follow-up work tracked in `BACKLOG-CHAT-ENTITLEMENTS-01`?
