# Class Views Role Capability Plan

## Goal
Implement class views so users see role-appropriate options:
- **Students**: view/select classes only.
- **Instructors**: view/select classes + edit class details.
- **Admins**: full management (add/create, edit, delete).

This plan assumes we should use existing store actions and API routes already present.

## Current baseline (from existing front-end)
- `ClassesView.vue` currently toggles only between student/instructor role views and renders class option cards.
- `classStore` already exposes CRUD actions:
  - `fetchClasses`
  - `createClass`
  - `updateClass`
  - `deleteClass`
- Role data is already available from auth state and used in class filtering.

## Role/capability matrix

| Capability | Student | Instructor | Admin |
|---|---:|---:|---:|
| View class list | ✅ | ✅ | ✅ |
| Select active class | ✅ | ✅ | ✅ |
| Edit class details | ❌ | ✅ | ✅ |
| Create class | ❌ | ❌ | ✅ |
| Delete class | ❌ | ❌ | ✅ |

## UX plan

### 1) Classes page structure
- Keep `ClassesView.vue` as container/orchestrator.
- Split UI into sections:
  1. `ClassListSection` (shared by all roles)
  2. `ClassDetailsEditor` (instructor + admin)
  3. `ClassAdminActions` (admin-only create/delete)

### 2) Student experience
- Show class list and selection state only.
- Hide edit/create/delete controls entirely.
- Keep action CTA text read-only oriented (e.g., "Instructor/contact" or "View details").

### 3) Instructor experience
- Show list + editable fields for selected class details.
- Save button triggers `classStore.updateClass(selectedId, patch)`.
- No create/delete controls displayed.

### 4) Admin experience
- Show instructor editing controls.
- Add class creation form (minimal required payload first).
- Add delete action for selected class with confirmation guard.

## Technical plan (front-end only)

### Container logic (`ClassesView.vue`)
- Derive capability flags from auth role:
  - `canEditClass = role === 'instructor' || role === 'admin'`
  - `canCreateClass = role === 'admin'`
  - `canDeleteClass = role === 'admin'`
- Keep role in sync from route params where applicable.
- Load classes on mount if missing.

### Components to introduce/refactor
- `components/classes/ClassDetailsEditor.vue`
  - Props: `selectedClass`, `isSaving`, `canEdit`
  - Emits: `save(patch)`
- `components/classes/ClassAdminActions.vue`
  - Props: `selectedClass`, `canCreate`, `canDelete`, `isSubmitting`
  - Emits: `create(payload)`, `delete(classId)`
- Optional:
  - `ClassViewPermissionsHint.vue` (small helper text explaining why controls are hidden).

### Data flow
- Source of truth remains `classStore` and `authStore`.
- CRUD calls remain in `classStore` actions; no direct API calls from components.
- Use local form state in editor/create components, then emit normalized payloads.

## Validation and safeguards
- Disable submit/delete buttons while corresponding action is loading.
- Display action errors from `classStore.actionStatus` near relevant controls.
- Require selected class before edit/delete actions.
- Confirm destructive delete action (modal or inline confirm).

## Implementation sequence
1. Add role capability computed flags in `ClassesView.vue`.
2. Extract details editing UI into `ClassDetailsEditor.vue`.
3. Gate editor visibility to instructor/admin only.
4. Add admin-only create/delete actions component.
5. Wire components to existing `classStore` CRUD actions.
6. Add loading/error states around each action.
7. Add/adjust unit tests for role-gated rendering and emitted CRUD events.

## Acceptance criteria
- Student sees no modify controls.
- Instructor can update class details but cannot create/delete classes.
- Admin can create, update, and delete classes.
- Existing class selection behavior still works.
- No new backend routes or store modules are introduced.

## Follow-up plan trigger
If payload mismatches are discovered while wiring create/update forms:
1. Document exact shape mismatch from existing endpoint responses.
2. Add a view-level mapper before proposing store contract changes.
3. If still blocked, create separate plan/PR for contract adjustments.
