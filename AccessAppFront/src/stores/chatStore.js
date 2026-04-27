import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../stores/helpers/actionStatus'
import { deriveSelectedId } from '../stores/helpers/selection'
import { toResourceError } from '../stores/helpers/apiErrors'

function normalizeChatTitle(title) {
  return String(title || '').trim().replace(/\s+/g, ' ')
}

export const useChatStore = defineStore('chats', {
  state: () => ({
    // Chat transcript state.
    chats: [],
    selectedChatId: null,

    // Model selection state (drives the model dropdown + persisted user choice).
    selectedModel: '',
    modelCatalog: [],
    modelCatalogLoading: false,
    modelCatalogError: '',
    modelCatalogFetchedAt: 0,
    lastPersistedSelection: '',

    // Request/order guards for async chat creation flow.
    newChatRequestId: 0,

    // Per-action CRUD/request status map (fetch/create/update/delete/message/ai keys).
    actionStatus: {}
  }),
  getters: {
    // Derived flag used by views/composables to know whether current selection still points to a real chat.
    hasActiveChat(state) {
      return state.selectedChatId !== null && state.chats.some((c) => c.id === state.selectedChatId)
    }
  },
  actions: {
    // --- State reset + local intent flags (setter-style helpers) ---

    // Clears all chat/model/session-local state, typically on logout or auth reset.
    resetChatState() {
      this.selectedChatId = null
      this.selectedModel = ''
      this.modelCatalog = []
      this.modelCatalogLoading = false
      this.modelCatalogError = ''
      this.modelCatalogFetchedAt = 0
      this.lastPersistedSelection = ''
      this.newChatRequestId = 0
      this.chats = []
      this.actionStatus = {}
    },
    // Marks that the next user prompt should create a fresh chat thread.
    // `newChatRequestId` lets consumers detect successive "new chat" intents even if other state is unchanged.
    prepareNewChat() {
      this.selectedChatId = null
      this.newChatRequestId += 1
    },

    // --- Model catalog + selection lifecycle ---

    // Loads model options for the dropdown, normalizes provider/id format, and restores persisted selection when possible.
    async fetchModelCatalog() {
      this.modelCatalogLoading = true
      this.modelCatalogError = ''
      try {
        const response = await api.get('/api/v1/ai/catalog')
        const payload = response?.data && typeof response.data === 'object' ? response.data : {}
        const options = []
        const models = Array.isArray(payload?.models) ? payload.models : []
        models.forEach((model) => {
          const provider = String(model?.provider || '').trim().toLowerCase()
          const modelId = String(model?.id || '').trim()
          if (!provider || !modelId) return
          options.push({
            value: `${provider}::${modelId}`,
            provider,
            modelId,
            label: `${modelId} (${provider})`
          })
        })

        // `modelCatalog` is the dropdown source; each option value is `${provider}::${modelId}`.
        this.modelCatalog = options
        const selectedProvider = String(payload?.selected?.provider || '').trim().toLowerCase()
        const selectedModelId = String(payload?.selected?.id || payload?.selected?.model_id || '').trim()
        const selectedValue = selectedProvider && selectedModelId ? `${selectedProvider}::${selectedModelId}` : ''
        const preferredSelected = selectedValue || this.lastPersistedSelection

        this.selectedModel = preferredSelected && options.some(
          (o) => o.value === preferredSelected)
          ? preferredSelected : options[0]?.value || ''
        this.modelCatalogFetchedAt = Date.now()
        this.lastPersistedSelection = selectedValue || this.lastPersistedSelection

      } catch (error) {
        this.modelCatalogError = 'Unable to load model inventory from /api/v1/ai/catalog. error: ' + (error?.message || 'unknown error')
        this.modelCatalog = []
        this.selectedModel = ''
        this.modelCatalogFetchedAt = 0
      } finally {
        this.modelCatalogLoading = false
      }
    },
    // Optimistically updates selected model and persists the provider/model pair to backend selection state.
    async updateModelSelection(selectedValue) {
      const normalizedValue = String(selectedValue || '').trim()
      if (!normalizedValue || !normalizedValue.includes('::')) return
      const [provider, modelId] = normalizedValue.split('::')
      if (!provider || !modelId) return

      this.selectedModel = normalizedValue

      try {
        const response = await api.post('/api/v1/ai/selection', { 
          provider, 
          model_id: modelId
        })
        const persistedProvider = String(response?.data?.provider || provider).trim().toLowerCase()
        const persistedModelId = String(response?.data?.id || response?.data?.model_id || modelId).trim()
        this.selectedModel = `${persistedProvider}::${persistedModelId}`
        this.lastPersistedSelection = this.selectedModel
      } catch {
        this.modelCatalogError = 'Unable to update model selection. Please try again.'
      }
    },
    // Fetches model catalog only when missing/stale to avoid repeated network calls in a single session.
    async ensureModelCatalogFreshForSession({ staleAfterMs = 300000 } = {}) {
      if (this.modelCatalogLoading) return
      const hasCatalog = this.modelCatalog.length > 0
      const isStale = !this.modelCatalogFetchedAt || (Date.now() - this.modelCatalogFetchedAt) > staleAfterMs
      if (hasCatalog && !isStale) return
      await this.fetchModelCatalog()
    },
    // Persists only when current selection differs from last backend-confirmed selection.
    async persistCurrentSelectionIfChanged() {
      const selectedValue = String(this.selectedModel || '').trim()
      if (!selectedValue || !selectedValue.includes('::')) return
      if (selectedValue === this.lastPersistedSelection) return
      await this.updateModelSelection(selectedValue)
    },
    // Session bootstrap helper that ensures both model options and persisted selected model are synchronized.
    async ensureModelSelectionForSession() {
      await this.ensureModelCatalogFreshForSession()
      await this.persistCurrentSelectionIfChanged()
    },

    // --- Chat collection CRUD + selection reconciliation ---

    // Fetches chat list and reconciles selected chat to a valid id when current selection no longer exists.
    async fetchChats() {
      const key = 'fetchChats'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/chats')
        const parsed = Array.isArray(response?.data) ? response.data : null
        if (!parsed) {
          const e = new Error('Chats response payload was malformed.')
          e.kind = 'resource'
          e.resource = 'chats'
          throw e
        }
        this.chats = parsed
        this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch (error) {
        const wrapped = error?.kind
          ? error
          : toResourceError(error, {
              resourceLabel: 'chats',
              unavailableMessage: 'Chats endpoint is currently unavailable. Please verify backend routes.',
              fallbackMessage: 'Unable to load chats.'
            })
        setActionError(this.actionStatus, key, wrapped.message)
        throw wrapped
      }
    },
    // Creates a chat with optimistic local insertion, then swaps temporary id with backend id on success.
    async createChat(payload) {
      const tempId = `temp-${Date.now()}`
      const key = `createChat:${tempId}`
      const sanitizedTitle = normalizeChatTitle(payload?.title || 'New Chat')
      const normalizedPayload = { ...payload, title: sanitizedTitle }
      const optimistic = { ...normalizedPayload, id: tempId }
      this.chats = [...this.chats, optimistic]
      this.selectedChatId = tempId
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: tempId })
      try {
        const response = await api.post('/api/v1/chats', normalizedPayload)
        this.chats = this.chats.map((c) => (c.id === tempId ? response.data : c))
        this.selectedChatId = response.data.id
        await this.ensureModelSelectionForSession()
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = this.chats.filter((c) => c.id !== tempId)
        this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
        setActionError(this.actionStatus, key, 'Unable to create chat.')
      }
    },
    // Applies optimistic patch updates to an existing chat and rolls back from snapshot on failure.
    async updateChat(chatId, patch) {
      const key = `updateChat:${chatId}`
      const snapshot = [...this.chats]
      const normalizedPatch = {
        ...patch,
        ...(Object.prototype.hasOwnProperty.call(patch || {}, 'title') ? { title: normalizeChatTitle(patch?.title) } : {})
      }
      this.chats = this.chats.map((c) => (c.id === chatId ? { ...c, ...normalizedPatch } : c))
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: chatId })
      try {
        const current = this.chats.find((c) => c.id === chatId)
        await api.put(`/api/v1/chats/${chatId}`, current)
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = snapshot
        setActionError(this.actionStatus, key, 'Unable to update chat.')
      }
    },
    // Optimistically removes a chat, reconciles selection, and restores previous snapshot if backend delete fails.
    async deleteChat(chatId) {
      const key = `deleteChat:${chatId}`
      const snapshot = [...this.chats]
      this.chats = this.chats.filter((c) => c.id !== chatId)
      this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: chatId })
      try {
        await api.delete(`/api/v1/chats/${chatId}`)
        this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = snapshot
        this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
        setActionError(this.actionStatus, key, 'Unable to delete chat.')
      }
    },
    // Ensures there is an active chat id for send-flow usage; creates one when nothing is currently selected.
    // This is used by prompt pipelines that require a concrete chat before creating messages/interactions.
    async ensureActiveChat(payload) {
      const existing = this.chats.find((c) => c.id === this.selectedChatId)
      if (existing) {
        return existing
      }

      const key = 'ensureActiveChat'
      setActionStatus(this.actionStatus, key, {loading: true, error: ''})
      try {
        const normalizedPayload = {
          ...payload,
          title: normalizeChatTitle(payload?.title || 'New Chat')
        }
        const response = await api.post('/api/v1/chats', normalizedPayload)
        this.chats = [...this.chats, response.data]
        this.selectedChatId = response.data.id
        await this.ensureModelSelectionForSession()
        setActionStatus(this.actionStatus, key, { loading: false, error: ''})
        return response.data
      } catch {
        setActionError(this.actionStatus, key, 'unable to start chat')
        throw new Error('unable to start chat')
      }
    },
    // Soft-remove/archive flow mirrors delete behavior but uses archive endpoint and rollback snapshot.
    async archiveChat(chatId) {
      const key = `archiveChat:${chatId}`
      const snapshot = [...this.chats]
      this.chats = this.chats.filter((c) => c.id !== chatId)
      this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: chatId })
      try {
        await api.patch(`/api/v1/chats/${chatId}/archive`)
        this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = snapshot
        this.selectedChatId = deriveSelectedId(this.selectedChatId, this.chats)
        setActionError(this.actionStatus, key, 'Unable to archive chat.')
      }
    },
    // Title-only edit endpoint with optimistic local rename and snapshot rollback behavior.
    async editChatTitle(chatId, title) {
      const key = `editChatTitle:${chatId}`
      const snapshot = [...this.chats]
      const normalizedTitle = normalizeChatTitle(title)
      this.chats = this.chats.map((chat) => (chat.id === chatId ? { ...chat, title: normalizedTitle } : chat))
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: chatId })
      try {
        await api.patch(`/api/v1/chats/${chatId}/edit-title`, { title: normalizedTitle })
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.chats = snapshot
        setActionError(this.actionStatus, key, 'Unable to edit chat title.')
      }
    },

    // --- Message + AI interaction fetch/create operations ---

    // Loads message history for a specific chat id.
    async fetchChatMessages(chatId) {
      const key = `fetchChatMessages:${chatId}`
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.get(`/api/v1/chats/${chatId}/messages`)
        const records = Array.isArray(response?.data) ? response.data : []
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
        return records
      } catch {
        setActionError(this.actionStatus, key, 'Unable to load chat messages.')
        throw new Error('Unable to load chat messages.')
      }
    },
    // Persists one user/assistant message record to backend.
    async createMessage(payload) {
      const key = 'createMessage'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/messages', payload)
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
        return response.data
      } catch {
        setActionError(this.actionStatus, key, 'Unable to save message.')
        throw new Error('Unable to save message.')
      }
    },
    // Requests assistant generation payload from backend for the current chat/message context.
    async requestAiInteraction(payload) {
      const key = 'requestAiInteraction'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/ai/interactions', payload)
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
        return response.data
      } catch (error) {
        setActionError(this.actionStatus, key, 'Unable to fetch assistant response.')
        throw error
      }
    },
    // Loads stored AI interaction records for a specific chat.
    async fetchChatInteractions(chatId) {
      const key = `fetchChatInteractions:${chatId}`
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.get(`/api/v1/chats/${chatId}/ai/interactions`)
        const records = Array.isArray(response?.data) ? response.data : []
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
        return records
      } catch {
        setActionError(this.actionStatus, key, 'Unable to load chat interactions.')
        throw new Error('Unable to load chat interactions.')
      }
    }
  }
})
