export function ensureActionState(existing) {
  return {
    loading: false,
    error: '',
    rollbackToken: null,
    ...(existing || {})
  }
}

export function setActionStatus(actionStatus, key, patch) {
  actionStatus[key] = {
    ...ensureActionState(actionStatus[key]),
    ...patch
  }
}

export function setActionError(actionStatus, key, message) {
  setActionStatus(actionStatus, key, { loading: false, error: message })
}