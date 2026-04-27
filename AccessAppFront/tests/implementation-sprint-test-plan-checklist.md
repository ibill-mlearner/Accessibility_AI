# Frontend UI + Composables QA Checklist

This replaces the old sprint checklist and tracks current cleanup/testing status for step 4.

## Scope reviewed
- `src/components/auth/*`
- `src/components/chat/*`
- `src/components/classes/*`
- `src/components/profile/*`
- `src/components/HeaderBar.vue`
- `src/components/SidebarNav.vue`
- `src/composables/*`
- related unit specs under `tests/unit/*`

## Current component inventory

### Auth components
- `LoginFormCard.vue`
- `LogoutButton.vue`
- `ProfileButton.vue`
- `AccountActionsCard.vue`

### Chat components
- `ComposerBar.vue`
- `ChatBubbleCard.vue`
- `ChatListItem.vue`
- `ReadAloudControls.vue`

### Classes components
- `ClassOptionCard.vue`
- `ClassDetailsEditor.vue`
- `ClassAdminActions.vue`
- `FeatureOptionCard.vue`

### Profile components
- `ProfileHeaderCard.vue`
- `ProfileSessionCard.vue`
- `ProfileSecurityCard.vue`
- `ProfileEmptyState.vue`
- `ProfileFontSizeSelect.vue`
- `ProfileColorblindFeatures.vue`
- `ProfileFontFamilyFeatures.vue`
- `ProfileAdminModelDownloadCard.vue`

### Navigation components
- `HeaderBar.vue`
- `SidebarNav.vue`

### Composables
- `useAutoScroll.js`
- `useChatTimeline.js`
- `useClassesViewState.js`
- `useFontFaceLoader.js`
- `useSendPrompt.js`
- `useAdminModelDownload.js`
- `useSpeechSynthesis.js`

## Current unit-test coverage snapshot

### Directly covered now
- `tests/unit/LoginView.spec.js` (auth login flow contract via store mocks)
- `tests/unit/authStore.spec.js`
- `tests/unit/ComposerBar.spec.js`
- `tests/unit/chatStore.modelSelection.spec.js`
- `tests/unit/HeaderBar.spec.js`
- `tests/unit/SidebarNav.spec.js`
- `tests/unit/ProfileAdminModelDownloadCard.spec.js`

### Not yet covered by dedicated component spec
- `LogoutButton.vue`, `ProfileButton.vue`, `AccountActionsCard.vue`
- `ChatBubbleCard.vue`, `ChatListItem.vue`, `ReadAloudControls.vue`
- `ClassOptionCard.vue`, `ClassDetailsEditor.vue`, `ClassAdminActions.vue`, `FeatureOptionCard.vue`
- `ProfileHeaderCard.vue`, `ProfileSessionCard.vue`, `ProfileSecurityCard.vue`, `ProfileEmptyState.vue`
- `ProfileFontSizeSelect.vue`, `ProfileColorblindFeatures.vue`, `ProfileFontFamilyFeatures.vue`

### Not yet covered by dedicated composable spec
- `useAutoScroll.js`
- `useChatTimeline.js`
- `useClassesViewState.js`
- `useFontFaceLoader.js`
- `useSendPrompt.js`
- `useAdminModelDownload.js`
- `useSpeechSynthesis.js`

## Stale items removed in this cleanup
- Removed old “NO LONGER NEEDED” checklist framing.
- Removed references to non-present specs (`LogoutView.spec.js`, `ClassesView.spec.js`, etc.).
- Removed outdated assertions that implied all contract suites were complete.

## Next test priorities (ordered)
1. Add auth component render/event tests (`LogoutButton`, `ProfileButton`, `AccountActionsCard`).
2. Add classes role-gated UI tests (editor/actions visible only for allowed roles).
3. Add chat component behavior tests (`ReadAloudControls`, `ChatListItem`, `ChatBubbleCard`).
4. Add profile-card render tests and event tests (`ProfileSecurityCard`, `ProfileHeaderCard`).
5. Add send-flow orchestration tests for retries/order guarantees at composable/store boundary.

## Composables workstreams (parallel planning)
1. **State & capability stream**: `useClassesViewState`, `useAutoScroll` (pure state transitions + role gates).
2. **Timeline stream**: `useChatTimeline`, `useSendPrompt` (ordering, retry, and error-envelope behaviors).
3. **Browser API stream**: `useSpeechSynthesis`, `useFontFaceLoader` (unsupported-browser guards + side-effect control).
4. **Admin action stream**: `useAdminModelDownload` (submit/cancel/progress lifecycle and abort semantics).

## Completion criteria for this section
- Every auth/chat/classes component has either:
  - a direct unit spec, or
  - documented rationale for indirect coverage.
- No docs in this folder reference removed files or obsolete sprint assumptions.
