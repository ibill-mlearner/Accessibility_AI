import { defineStore } from 'pinia'
import api from '../services/api'
import { useChatStore } from './chatStore'
import { useClassStore } from './classStore'
import { useFeatureStore } from './featureStore'

function buildGuestState() {
  return {
    role: 'guest',
    user: null,
    currentUser: null,
    isAuthenticated: false,
    authError: '',
    session: null,
    allowedActions: [],
    sessionChecked: false
  }
}


export const useAuthStore = defineStore('auth', {
    state: () => buildGuestState(),
    actions:
    { applyAuthenticatedUser(userLike = {}) {
        const hasIdentity = Boolean(userLike?.id)
        const knownEmail = userLike?.email || this.currentUser?.email || null
        this.currentUser = hasIdentity ? { id: userLike.id, email: knownEmail} : null
        this.user = this.currentUser
        this.isAuthenticated = hasIdentity
        this.role = userLike?.role || (hasIdentity ? 'authenticated' : 'guest')
        this.authError = ''

    }, clearAuthState() {
        const chatStore = useChatStore()
        const classStore = useClassStore()
        const featureStore = useFeatureStore()
        const guestState = buildGuestState()
        this.role = guestState.role
        this.user = guestState.user
        this.currentUser = guestState.currentUser
        this.isAuthenticated = guestState.isAuthenticated
        this.authError = guestState.authError
        this.session = guestState.session
        this.allowedActions = guestState.allowedActions
        this.sessionChecked = guestState.sessionChecked
        chatStore.resetChatState()
        classStore.resetClassState()
        featureStore.resetFeatureState()
        if (typeof document !== 'undefined') {
            document.documentElement.style.removeProperty('font-size')
            document.documentElement.style.removeProperty('font-family')
        }

    }, async initFromSession() {
        return this.me()


    }, async login({email, password} = {}) {
        this.authError = ''
        try {
            const chatStore = useChatStore()
            const response = await api.post('/api/v1/auth/login', { email, password })
            this.applyAuthenticatedUser(response?.data?.user || {})
            chatStore.resetChatState()
            await this.me()
            await chatStore.ensureModelSelectionForSession()
            return true
        } catch (error) {
            this.clearAuthState()
            this.sessionChecked = true
            const status = error?.response?.status
            if (status === 400 || status === 401) {
              this.authError = 'Invalid email or password.'
            } else {
              this.authError = 'Unable to log in right now. Please try again.'
            }
            throw error
        }
    },

    async register({ email, password, role}) {
        // const temp = keyword -- password for registering as admin maybe?
        this.authError = ''
        try {
            const chatStore = useChatStore()
            const response = await api.post('/api/v1/auth/register', { email, password, role })
            this.applyAuthenticatedUser(response?.data?.user || {})
            chatStore.resetChatState()
            await this.me()
            await chatStore.ensureModelSelectionForSession()
            return true
        } catch (error) {
            this.clearAuthState()
            const status = error?.response?.status
            if (status === 400) {
            this.authError = 'Email and password are required.'
            } else if (status === 409) {
                this.authError = 'Email is already registered.'
            } else {
                this.authError = 'Unable to register right now. Please try again.' }
            throw error
        }
    }, async me() {
        this.authError = ''
        try {
            const response = await api.get('/api/v1/auth/session')
            const sessionPayload = response?.data || {}
            const userPayload = sessionPayload?.user || {}

            this.applyAuthenticatedUser(userPayload)
            this.session = sessionPayload?.session || null
            this.allowedActions = Array.isArray(
                sessionPayload?.session?.allowed_actions) ? sessionPayload.session.allowed_actions : []
            this.sessionChecked = true
            return true
        } catch ( error ) {
            this.clearAuthState()
            const status = error?.response?.status
            if (status === 401) {
            this.authError = 'Your session is invalid or expired. Please sign in again.'
            } else {
              this.authError = 'Unable to verify session right now. Please try again.'
            }
            return false
        }
    }, async logout() {
        try {
            await api.post('/api/v1/auth/logout')
        } catch {
        // Local state still clears even when backend session is already missing/expired.
        } finally {
            this.clearAuthState()
        }

    },setRole(role) {
        this.role = role || (this.isAuthenticated ? this.role: 'guest')
    }}
})
