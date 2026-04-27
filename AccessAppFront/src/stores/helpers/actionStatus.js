/** Shared helpers for consistent per-action loading/error/rollback state in stores. */
export function ensureActionState(existing) {
  // Merges caller state with default action-status fields used by store action maps.
  return {
    loading: false,
    error: '',
    rollbackToken: null,
    ...(existing || {})
  }
}

export function setActionStatus(actionStatus, key, patch) {
  // Upserts one action-status entry so UI can read deterministic loading/error flags by key.
  actionStatus[key] = {
    ...ensureActionState(actionStatus[key]),
    ...patch
  }
}

export function setActionError(actionStatus, key, message) {
  // Convenience wrapper for terminal error state while clearing loading for the action.
  setActionStatus(actionStatus, key, { loading: false, error: message })
}
