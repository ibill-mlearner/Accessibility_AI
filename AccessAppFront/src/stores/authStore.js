import { defineStore } from 'pinia'
import api from '../services/api'
import { persistSession, hydrateSession, clearSession } from '../lib/sessionMirror'


export const useAuthStore = defineStore('auth', {
    state: () => ({
        role: 'guest',
        user: null,
        currentUser: null,
        isAuthenticated: false,
        authError: ''
  }),
  actions: {
    initFromSession() {
        const hydrated = hydrateSession()
        if (!hydrated) return
        if (hydrated.clear) {
        this.logout()
        return
        }

        // localStorage.setItem('token', response.data.token)
        // moving away from hydration
        this.currentUser = hydrated.currentUser
        this.user = hydrated.user
        this.isAuthenticated = hydrated.isAuthenticated
        this.role = hydrated.role
        this.authError = ''
    },
    async login({ email, password }) {
        this.authError = ''
        const response = await api.post('/api/v1/auth/login', { email, password })
        const u = response?.data?.user || {}
        const ok = Boolean(u.id && u.email)



        this.currentUser = ok ? { id: u.id, email: u.email } : null
        this.user = this.currentUser
        this.isAuthenticated = ok
        this.role = u.role || (ok ? 'authenticated' : 'guest')
        persistSession({ role: this.role, currentUser: this.currentUser, isAuthenticated: this.isAuthenticated })
        return true
    },
    logout() {
        this.role = 'guest'
        this.currentUser = null
        this.user = null
        this.isAuthenticated = false
        this.authError = ''
        clearSession()
    },
    setRole(role) {
        this.role = role
        if (this.isAuthenticated) {
            persistSession({ role: this.role, currentUser: this.currentUser, isAuthenticated: this.isAuthenticated })
        }
    }}
})