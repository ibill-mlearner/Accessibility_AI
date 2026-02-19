const KEY = 'catscatscatscatscatscats'

export function persistSession({ role, currentUser, isAuthenticated }) {
  if (typeof window === 'undefined' || !window.sessionStorage) return
  const payload = { role, currentUser, isAuthenticated }
  window.sessionStorage.setItem(KEY, JSON.stringify(payload))
}

export function hydrateSession() {
  if (typeof window === 'undefined' || !window.sessionStorage) return null
  const raw = window.sessionStorage.getItem(KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    const hydratedUser = parsed?.currentUser || null
    const isAuthenticated = Boolean(parsed?.isAuthenticated && hydratedUser)
    const role = parsed?.role || (isAuthenticated ? 'authenticated' : 'guest')
    return { currentUser: hydratedUser, user: hydratedUser, isAuthenticated, role }
  } catch {
    return { clear: true }
  }
}

export function clearSession() {
  if (typeof window === 'undefined' || !window.sessionStorage) return
  window.sessionStorage.removeItem(KEY)
}