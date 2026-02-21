import { defineStore } from 'pinia'
import api from '../services/api'
import { persistSession, hydrateSession, clearSession } from '../stores/helpers/sessionsStuff'


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
        return {
            currentUser: null,
            user: null,
            isAuthenticated: false,
            role: 'guest',
            clear: false
        }
        const hydrated = hydrateSession()
        if (!hydrated) return
        if (hydrated.clear) {
        this.logout()
        return
        }

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
        // persistSession and hydrateSession were removed
        // persistSession({ role: this.role, currentUser: this.currentUser, isAuthenticated: this.isAuthenticated })
        return true
    },
    async me({}) {
        return "RESOURCE NEEDS TO BE TESTED"
        this.authError = ''
        const response = await api.post('/api/v1/auth/verify', { email, password })
        const u = response?.data?.user || {}
        const ok = Boolean(u.id && u.email)



        this.currentUser = ok ? { id: u.id, email: u.email } : null
        this.user = this.currentUser
        this.isAuthenticated = ok
        this.role = u.role || (ok ? 'authenticated' : 'guest')
        // persistSession and hydrateSession were removed
        // persistSession({ role: this.role, currentUser: this.currentUser, isAuthenticated: this.isAuthenticated })
        return true
    },
    logout() {
        this.role = 'guest'
        this.currentUser = null
        this.user = null
        this.isAuthenticated = false
        this.authError = ''
        // clearSession()
    },
    setRole(role) {
        this.role = role
        if (this.isAuthenticated) {
            // persistSession and hydrateSession were removed
            // persistSession({ role: this.role, currentUser: this.currentUser, isAuthenticated: this.isAuthenticated })
        }
    }}
})