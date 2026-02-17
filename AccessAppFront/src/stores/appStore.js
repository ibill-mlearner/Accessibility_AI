import { defineStore } from 'pinia'
import api from '../services/api'

/**
 * App Store Refactor Design (pre-implementation)
 *
 * Goal: Move from a single bootstrap-centric loading flow to resource-oriented
 * actions with explicit selection derivation, mutation strategy, and rollback.
 *
 * Planned resource actions
 * - Chats:
 *   - fetchChats()
 *   - createChat(payload)
 *   - updateChat(chatId, patch)
 *   - deleteChat(chatId)
 * - Classes:
 *   - fetchClasses()
 *   - createClass(payload)
 *   - updateClass(classId, patch)
 *   - deleteClass(classId)
 * - Notes:
 *   - fetchNotes()
 *   - createNote(payload)
 *   - updateNote(noteId, patch)
 *   - deleteNote(noteId)
 * - Features:
 *   - fetchFeatures()
 *   - updateFeature(featureId, patch)
 *
 * bootstrap() becomes an orchestration utility only:
 * - Promise.all([fetchChats, fetchClasses, fetchNotes, fetchFeatures])
 * - no direct assignment or implicit first-item selection logic.
 *
 * Mutation strategy by path (optimistic vs pessimistic)
 * - createChat: optimistic insert with temporary id, reconcile with server id.
 * - updateChat: optimistic patch + rollback snapshot on failure.
 * - deleteChat: optimistic remove + rollback on failure.
 * - createClass: pessimistic (permission/role sensitivity), append on success.
 * - updateClass: pessimistic to avoid invalid role/class visibility flicker.
 * - deleteClass: pessimistic because it can invalidate selectedClassId.
 * - createNote/updateNote/deleteNote: optimistic for fast editing UX,
 *   rollback on API failure.
 * - updateFeature: pessimistic until feature-gating side effects are isolated.
 *
 * Selected-id derivation/revalidation plan
 * - Derive selectedChatId via deriveSelectedChatId(prevSelectedId, chats):
 *   1) preserve previous selection if still present
 *   2) otherwise choose first stable item by explicit sort key (not array order)
 *   3) else null
 * - Derive selectedClassId similarly via deriveSelectedClassId(...).
 * - Revalidate selected ids after every fetch* and delete* action.
 * - When role changes, selectedClassId resets and is re-derived from roleClasses
 *   after fetchClasses() completes.
 *
 * Error and rollback strategy (per-action, not global-only)
 * - Add actionStatus map keyed by action name/resource id:
 *   e.g. actionStatus['updateChat:12'] = { loading, error, rollbackToken }.
 * - Keep global error only for page-level fallback messaging.
 * - Each mutation stores rollback snapshot/token before optimistic write.
 * - On failure: rollback local state, set action-scoped error, preserve UX context.
 * - On success: clear action-scoped error and rollback token.
 *
 * Migration compatibility note
 * - Current selection relies on seeded mock ordering (chats[0]).
 * - Refactor must remove implicit ordering assumptions by introducing
 *   deterministic sort keys (createdAt/id) and explicit derivation helpers.
 * - During migration, keep a compatibility fallback to first item only when
 *   no stable key exists, then remove after data contract is updated.
 */

export const useAppStore = defineStore('app', {
  state: () => ({
    role: 'guest',
    user: null,
    authError: '',
    selectedChatId: null,
    selectedClassId: null,
    selectedModel: '',
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
      return state.classes.filter((item) => item.role === state.role)
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
    // ---------------------------------------------------------------------
    // Chat + AI interaction resource actions
    // Includes list loading and optimistic CRUD behavior for active sessions.
    // ---------------------------------------------------------------------
    async fetchChats() {
      const actionKey = 'fetchChats'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/chats')
        this.chats = response.data
        this.selectedChatId = this.deriveSelectedId(this.selectedChatId, this.chats)
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to load chats.')
        throw new Error('Unable to load chats.')
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
      } catch {
        this.setActionError(actionKey, 'Unable to load classes.')
        throw new Error('Unable to load classes.')
      }
    },
    async fetchNotes() {
      const actionKey = 'fetchNotes'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/notes')
        this.notes = response.data
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to load notes.')
        throw new Error('Unable to load notes.')
      }
    },
    async fetchFeatures() {
      const actionKey = 'fetchFeatures'
      this.setActionStatus(actionKey, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/features')
        this.features = response.data
        this.setActionStatus(actionKey, { loading: false, error: '' })
      } catch {
        this.setActionError(actionKey, 'Unable to load features.')
        throw new Error('Unable to load features.')
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
      this.error = ''
      try {
        await Promise.all([this.fetchChats(), this.fetchClasses(), this.fetchNotes(), this.fetchFeatures()])
      } catch (error) {
        this.error = 'Unable to load data from the backend service. Please try again.'
      } finally {
        this.loading = false
      }
    },
    async login({ email, password }) {
      this.authError = ''
      try {
        const response = await api.post('/api/v1/auth/login', { email, password })
        const authenticatedUser = response?.data?.user || {}
        const hasAuthenticatedIdentity = Boolean(authenticatedUser.id && authenticatedUser.email)

        this.user = {
          id: authenticatedUser.id,
          email: authenticatedUser.email
        }

        this.role = authenticatedUser.role || (hasAuthenticatedIdentity ? 'authenticated' : 'guest')
        return true
      } catch (error) {
        this.user = null
        this.role = 'guest'
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
      this.user = null
      this.authError = ''
      this.selectedClassId = null
    },
    setRole(role) {
      this.role = role
      this.selectedClassId = null
      this.selectedClassId = this.deriveSelectedId(this.selectedClassId, this.roleClasses)
    }
  }
})
