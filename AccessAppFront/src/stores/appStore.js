import { defineStore } from 'pinia'
import api from '../services/api'

const SESSION_STORAGE_KEY = 'accessapp:session'
// Client-side key used to mirror backend-authenticated identity in sessionStorage.

/**
 * App Store architecture notes
 *
 * This store centralizes auth/session state, resource fetching, and
 * optimistic/pessimistic mutation handling for core app entities.
 *
 * Resource action groups
 * - Chats: fetch/create/update/delete
 * - Classes: fetch/create/update/delete
 * - Notes: fetch/create/update/delete
 * - Features: fetch/update
 *
 * bootstrap() orchestration
 * - Runs fetchChats/fetchClasses/fetchNotes/fetchFeatures in parallel.
 * - Aggregates auth/resource failures into user-facing top-level messages.
 *
 * Mutation strategy highlights
 * - Chats/notes favor optimistic UX where rollback is practical.
 * - Classes/features remain more pessimistic where permission or gating
 *   side effects can cause misleading intermediate UI.
 *
 * Selection derivation and revalidation
 * - selected ids are re-derived after relevant fetch/delete updates.
 * - previous valid selection is preserved when still present.
 * - fallback selection uses stable sort keys (createdAt/start/id).
 *
 * Action-level status and errors
 * - actionStatus is keyed per action/resource id for granular loading/error UI.
 * - global `error` is reserved for broader page-level fallback messaging.
 *
 * Migration context
 * - Legacy behavior relied on implicit first-item ordering.
 * - Current helpers aim to keep selection deterministic while backend
 *   contracts converge on stable ordering keys.
 */

export const useAppStore = defineStore('app', {
  state: () => ({
    role: 'guest',
    user: null,
    currentUser: null,
    isAuthenticated: false,
    authError: '',
    selectedChatId: null,
    selectedClassId: null,
    selectedModel: '',
    newChatRequestId: 0,
    chats: [],
    classes: [],
    notes: [],
    features: [],
    actionStatus: {},
    loading: false,
    error: ''
  }),
  getters: {
    selectedClass(state) {
      return state.classes.find((item) => item.id === state.selectedClassId) || null
    },
    hasActiveChat(state) {
      return state.selectedChatId !== null && state.chats.some((chat) => chat.id === state.selectedChatId)
    },
    hasHeaderContext() {
      return Boolean(this.selectedModel && this.hasActiveChat && this.selectedClass)
    },
    topHeader() {
      if (!this.hasHeaderContext) return ''
      return `${this.selectedModel}     ${this.selectedClass.name}`
    },
    roleClasses(state) {
      if (state.role === 'guest') return []
      const matchingClasses = state.classes.filter((item) => item.role === state.role)
      return matchingClasses.length ? matchingClasses : state.classes
    }
  },
  actions: {
    // ---------------------------------------------------------------------
    // Store-wide utilities
    // Shared helpers used across chat/class/note/feature workflows.
    // ---------------------------------------------------------------------
    setActionStatus(actionKey, patch) {
      this.actionStatus[actionKey] = {
        loading: false,
        error: '',
        rollbackToken: null,
        ...(this.actionStatus[actionKey] || {}),
        ...patch
      }
    },
    setActionError(actionKey, message) {
      this.setActionStatus(actionKey, { loading: false, error: message })
    },
    sortedByStableKey(items) {
      return [...items].sort((a, b) => {
        const aKey = a.createdAt || a.start || a.id || Number.MAX_SAFE_INTEGER
        const bKey = b.createdAt || b.start || b.id || Number.MAX_SAFE_INTEGER
        if (aKey < bKey) return -1
        if (aKey > bKey) return 1
        return 0
      })
    },
    deriveSelectedId(previousId, items) {
      if (!items.length) return null
      if (previousId !== null && items.some((item) => item.id === previousId)) {
        return previousId
      }
      return this.sortedByStableKey(items)[0]?.id ?? items[0]?.id ?? null
    },
    isEndpointUnavailableStatus(status) {
      return [404, 405, 501, 502, 503].includes(status)
    },
    toResourceError(error, { resourceLabel, unavailableMessage, fallbackMessage }) {
      const status = error?.response?.status
      if (status === 401 || status === 403) {
        const authError = new Error(`${resourceLabel} requires authentication.`)
        authError.kind = 'auth'
        authError.status = status
        authError.resource = resourceLabel
        return authError
      }

      if (this.isEndpointUnavailableStatus(status)) {
        const unavailableError = new Error(unavailableMessage)
        unavailableError.kind = 'unavailable'
        unavailableError.status = status
        unavailableError.resource = resourceLabel
        return unavailableError
      }

      const resourceError = new Error(fallbackMessage)
      resourceError.kind = 'resource'
      resourceError.status = status
      resourceError.resource = resourceLabel
      return resourceError
    },
    parseCollectionItems(payload) {
      if (Array.isArray(payload)) return payload
      return null
    },
    persistSession() {
      if (typeof window === 'undefined' || !window.sessionStorage) return
      // Persist only UI-facing auth context; backend authorization still depends on cookie session.

      const payload = {
        role: this.role,
        currentUser: this.currentUser,
        isAuthenticated: this.isAuthenticated
      }

      window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload))
      // Writes role/currentUser/isAuthenticated so refresh restores UI state.
    },
    hydrateSession() {
      if (typeof window === 'undefined' || !window.sessionStorage) return
      // Hydration is local-first and runs before any backend verification request.

      const rawSession = window.sessionStorage.getItem(SESSION_STORAGE_KEY)
      // No persisted mirror means retain default guest state.
      if (!rawSession) return

      try {
        const parsed = JSON.parse(rawSession)
        const hydratedUser = parsed?.currentUser || null

        this.currentUser = hydratedUser
        this.user = hydratedUser
        this.isAuthenticated = Boolean(parsed?.isAuthenticated && hydratedUser)
        this.role = parsed?.role || (this.isAuthenticated ? 'authenticated' : 'guest')
        // Role falls back to authenticated/guest when explicit role is missing in stored payload.
        this.authError = ''
      } catch {
        this.logout()
        // Malformed stored state is treated as invalid and reset via logout path.
      }
    },
    clearSession() {
      if (typeof window === 'undefined' || !window.sessionStorage) return
      window.sessionStorage.removeItem(SESSION_STORAGE_KEY)
      // Removes client mirror; does not directly clear server session cookie.
    },
    // ---------------------------------------------------------------------
    // Chat + AI interaction resource actions
    // Includes list loading and optimistic CRUD behavior for active sessions.
    // ---------------------------------------------------------------------
    async fetchChats() {
      const actionKey = 'fetchChats'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/chats')
        const parsedChats = this.parseCollectionItems(response?.data)
        if (!parsedChats) {
          const malformedPayloadError = new Error('Chats response payload was malformed.')
          malformedPayloadError.kind = 'resource'
          malformedPayloadError.resource = 'chats'
          throw malformedPayloadError
        }
        this.chats = parsedChats
        this.selectedChatId = this.deriveSelectedId(this.selectedChatId, this.chats)
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch (error) {
        const wrappedError = error?.kind
          ? error
          : this.toResourceError(error, {
              resourceLabel: 'chats',
              unavailableMessage: 'Chats endpoint is currently unavailable. Please verify backend routes.',
              fallbackMessage: 'Unable to load chats.'
            })
        this.setActionError(actionKey, wrappedError.message)
        throw wrappedError
      }
    },
    async fetchClasses() {
      const actionKey = 'fetchClasses'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/classes')
        this.classes = response.data
        this.selectedClassId = this.deriveSelectedId(this.selectedClassId, this.roleClasses)
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch (error) {
        const wrappedError = this.toResourceError(error, {
          resourceLabel: 'classes',
          unavailableMessage: 'Classes endpoint is unavailable. Enable /api/v1/classes or disable class-dependent UI.',
          fallbackMessage: 'Unable to load classes.'
        })
        this.setActionError(actionKey, wrappedError.message)
        throw wrappedError
      }
    },
    async fetchNotes() {
      const actionKey = 'fetchNotes'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/notes')
        this.notes = response.data
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch (error) {
        const wrappedError = this.toResourceError(error, {
          resourceLabel: 'notes',
          unavailableMessage: 'Notes endpoint is unavailable. Enable /api/v1/notes or hide notes functionality.',
          fallbackMessage: 'Unable to load notes.'
        })
        this.setActionError(actionKey, wrappedError.message)
        throw wrappedError
      }
    },
    async fetchFeatures() {
      const actionKey = 'fetchFeatures'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/features')
        this.features = response.data
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch (error) {
        const wrappedError = this.toResourceError(error, {
          resourceLabel: 'features',
          unavailableMessage: 'Features endpoint is unavailable. Enable /api/v1/features or disable feature toggles.',
          fallbackMessage: 'Unable to load features.'
        })
        this.setActionError(actionKey, wrappedError.message)
        throw wrappedError
      }
    },
    async createChat(payload) {
      const tempId = `temp-${Date.now()}`
      const optimisticChat = { ...payload, id: tempId }
      const actionKey = `createChat:${tempId}`
      this.chats = [...this.chats, optimisticChat]
      this.selectedChatId = tempId
      this.setActionStatus(actionKey, { loading: true, error: '', rollbackToken: tempId })
      try {
        const response = await api.post('/api/v1/chats', payload)
        this.chats = this.chats.map((chat) => (chat.id === tempId ? response.data : chat))
        this.selectedChatId = response.data.id
        this.setActionStatus(actionKey, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = this.chats.filter((chat) => chat.id !== tempId)
        this.selectedChatId = this.deriveSelectedId(this.selectedChatId, this.chats)
        this.setActionError(actionKey, 'Unable to create chat.')
      }
    },
    prepareNewChat() {
      this.selectedChatId = null
      this.newChatRequestId += 1
    },
    async ensureActiveChat(payload) {
      const existing = this.chats.find((chat) => chat.id === this.selectedChatId)
      if (existing) return existing

      const actionKey = 'ensureActiveChat'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/chats', payload)
        this.chats = [...this.chats, response.data]
        this.selectedChatId = response.data.id
        this.setActionStatus(actionKey, { loading: false, error: '' })
        return response.data
      } catch {
        this.setActionError(actionKey, 'Unable to start chat.')
        throw new Error('Unable to start chat.')
      }
    },
    async createMessage(payload) {
      const actionKey = 'createMessage'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/messages', payload)
        this.setActionStatus(actionKey, { loading: false, error: '' })
        return response.data
      } catch {
        this.setActionError(actionKey, 'Unable to save message.')
        throw new Error('Unable to save message.')
      }
    },
    async requestAiInteraction(payload) {
      const actionKey = 'requestAiInteraction'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/ai/interactions', payload)
        this.setActionStatus(actionKey, { loading: false, error: '' })
        return response.data
      } catch (error) {
        this.setActionError(actionKey, 'Unable to fetch assistant response.')
        throw error
      }
    },
    async updateChat(chatId, patch) {
      const actionKey = `updateChat:${chatId}`
      const snapshot = [...this.chats]
      this.chats = this.chats.map((chat) => (chat.id === chatId ? { ...chat, ...patch } : chat))
      this.setActionStatus(actionKey, { loading: true, error: '', rollbackToken: chatId })
      try {
        const current = this.chats.find((chat) => chat.id === chatId)
        await api.put(`/api/v1/chats/${chatId}`, current)
        this.setActionStatus(actionKey, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = snapshot
        this.setActionError(actionKey, 'Unable to update chat.')
      }
    },
    async deleteChat(chatId) {
      const actionKey = `deleteChat:${chatId}`
      const snapshot = [...this.chats]
      this.chats = this.chats.filter((chat) => chat.id !== chatId)
      this.selectedChatId = this.deriveSelectedId(this.selectedChatId, this.chats)
      this.setActionStatus(actionKey, { loading: true, error: '', rollbackToken: chatId })
      try {
        await api.delete(`/api/v1/chats/${chatId}`)
        this.selectedChatId = this.deriveSelectedId(this.selectedChatId, this.chats)
        this.setActionStatus(actionKey, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = snapshot
        this.selectedChatId = this.deriveSelectedId(this.selectedChatId, this.chats)
        this.setActionError(actionKey, 'Unable to delete chat.')
      }
    },
    // ---------------------------------------------------------------------
    // Class management actions
    // Scoped to role-aware class visibility and pessimistic server confirmation.
    // ---------------------------------------------------------------------
    async createClass(payload) {
      const actionKey = 'createClass'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/classes', payload)
        this.classes = [...this.classes, response.data]
        this.selectedClassId = this.deriveSelectedId(this.selectedClassId, this.roleClasses)
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to create class.')
      }
    },
    async updateClass(classId, patch) {
      const actionKey = `updateClass:${classId}`
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const previous = this.classes.find((item) => item.id === classId) || {}
        const response = await api.put(`/api/v1/classes/${classId}`, { ...previous, ...patch })
        this.classes = this.classes.map((item) => (item.id === classId ? response.data : item))
        this.selectedClassId = this.deriveSelectedId(this.selectedClassId, this.roleClasses)
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to update class.')
      }
    },
    async deleteClass(classId) {
      const actionKey = `deleteClass:${classId}`
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        await api.delete(`/api/v1/classes/${classId}`)
        this.classes = this.classes.filter((item) => item.id !== classId)
        this.selectedClassId = this.deriveSelectedId(this.selectedClassId, this.roleClasses)
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to delete class.')
      }
    },
    // ---------------------------------------------------------------------
    // Notes actions
    // Optimized for editing speed with rollback support on API failure.
    // ---------------------------------------------------------------------
    async createNote(payload) {
      const tempId = `temp-${Date.now()}`
      const optimisticNote = { ...payload, id: tempId }
      const actionKey = `createNote:${tempId}`
      this.notes = [...this.notes, optimisticNote]
      this.setActionStatus(actionKey, { loading: true, error: '', rollbackToken: tempId })
      try {
        const response = await api.post('/api/v1/notes', payload)
        this.notes = this.notes.map((note) => (note.id === tempId ? response.data : note))
        this.setActionStatus(actionKey, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.notes = this.notes.filter((note) => note.id !== tempId)
        this.setActionError(actionKey, 'Unable to create note.')
      }
    },
    async updateNote(noteId, patch) {
      const actionKey = `updateNote:${noteId}`
      const snapshot = [...this.notes]
      this.notes = this.notes.map((note) => (note.id === noteId ? { ...note, ...patch } : note))
      this.setActionStatus(actionKey, { loading: true, error: '', rollbackToken: noteId })
      try {
        const current = this.notes.find((note) => note.id === noteId)
        await api.put(`/api/v1/notes/${noteId}`, current)
        this.setActionStatus(actionKey, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.notes = snapshot
        this.setActionError(actionKey, 'Unable to update note.')
      }
    },
    async deleteNote(noteId) {
      const actionKey = `deleteNote:${noteId}`
      const snapshot = [...this.notes]
      this.notes = this.notes.filter((note) => note.id !== noteId)
      this.setActionStatus(actionKey, { loading: true, error: '', rollbackToken: noteId })
      try {
        await api.delete(`/api/v1/notes/${noteId}`)
        this.setActionStatus(actionKey, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.notes = snapshot
        this.setActionError(actionKey, 'Unable to delete note.')
      }
    },
    // ---------------------------------------------------------------------
    // Feature controls
    // Kept pessimistic while feature-gating side effects are still evolving.
    // ---------------------------------------------------------------------
    async updateFeature(featureId, patch) {
      const actionKey = `updateFeature:${featureId}`
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const previous = this.features.find((item) => item.id === featureId) || {}
        const response = await api.put(`/api/v1/features/${featureId}`, { ...previous, ...patch })
        this.features = this.features.map((item) => (item.id === featureId ? response.data : item))
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to update feature.')
      }
    },
    // ---------------------------------------------------------------------
    // App lifecycle + session role actions
    // bootstrap orchestrates resource fetches without owning resource logic.
    // ---------------------------------------------------------------------
    async bootstrap() {
      this.loading = true
      // Bootstrap validates effective auth by attempting protected resource reads.
      this.error = ''
      this.authError = ''

      const results = await Promise.allSettled([
        this.fetchChats(),
        this.fetchClasses(),
        this.fetchNotes(),
        this.fetchFeatures()
      ])

      const failures = results.filter((result) => result.status === 'rejected').map((result) => result.reason)

      if (failures.some((error) => error?.kind === 'auth')) {
        this.authError = 'Your session is invalid or expired. Please sign in again.'
        // Auth failure here indicates backend session is not valid for protected endpoints.
      }

      const hasResourceFailure = failures.some((error) => error?.kind !== 'auth')
      if (hasResourceFailure) {
        this.error = 'Some application resources could not be loaded from the backend service.'
      }

      this.loading = false
    },
    async login({ email, password }) {
      this.authError = ''
      try {
        const response = await api.post('/api/v1/auth/login', { email, password })
        // Backend login endpoint establishes Flask-Login session cookie.
        const authenticatedUser = response?.data?.user || {}
        const hasAuthenticatedIdentity = Boolean(authenticatedUser.id && authenticatedUser.email)

        this.currentUser = {
          id: authenticatedUser.id,
          email: authenticatedUser.email
        }
        this.user = this.currentUser
        this.isAuthenticated = hasAuthenticatedIdentity

        this.role = authenticatedUser.role || (hasAuthenticatedIdentity ? 'authenticated' : 'guest')
        this.persistSession()
        // Client sessionStorage mirrors authenticated identity returned by backend.
        return true
      } catch (error) {
        this.currentUser = null
        this.user = null
        this.isAuthenticated = false
        this.role = 'guest'
        this.clearSession()
        const status = error?.response?.status
        if (status === 400 || status === 401) {
          this.authError = 'Invalid email or password.'
        } else {
          this.authError = 'Unable to log in right now. Please try again.'
        }
        throw error
      }
    },
    logout() {
      this.role = 'guest'
      this.currentUser = null
      this.user = null
      this.isAuthenticated = false
      this.authError = ''
      this.selectedClassId = null
      this.clearSession()
      // Frontend logout clears local mirror immediately; backend logout endpoint is separate.
    },
    setRole(role) {
      this.role = role
      this.selectedClassId = null
      this.selectedClassId = this.deriveSelectedId(this.selectedClassId, this.roleClasses)
      if (this.isAuthenticated) {
        this.persistSession()
      }
    }
  }
})
