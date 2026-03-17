import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../stores/helpers/actionStatus'
import { deriveSelectedId } from '../stores/helpers/selection'
import { toResourceError } from '../stores/helpers/apiErrors'

export const useChatStore = defineStore('chats', {
  state: () => ({
    selectedChatId: null,
    selectedModel: '',
    modelCatalog: [],
    modelCatalogLoading: false,
    modelCatalogError: '',
    modelCatalogFetchedAt: 0,
    lastPersistedSelection: '',
    newChatRequestId: 0,
    chats: [],
    actionStatus: {}
  }),
  getters: {
    hasActiveChat(state) {
      return state.selectedChatId !== null && state.chats.some((c) => c.id === state.selectedChatId)
    }
  },
  actions: {
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
    async fetchModelCatalog() {
      this.modelCatalogLoading = true
      this.modelCatalogError = ''
      try {
        const response = await api.get('/api/v1/ai/models/available')
        const payload = response?.data && typeof response.data === 'object' ? response.data : {}
        const defaults = payload?.provider_defaults && typeof payload.provider_defaults === 'object'
          ? payload.provider_defaults
          : {}
        const defaultProvider = String(defaults?.provider || '').trim().toLowerCase()
        const options = []

        const normalizeProvider = (bucketName) => {
          const normalizedBucket = String(bucketName || '').trim().toLowerCase()
          if (!normalizedBucket) return ''
          if (normalizedBucket === 'local' || normalizedBucket === 'huggingface_local') {
            return defaultProvider || 'huggingface'
          }
          return normalizedBucket
        }

        Object.entries(payload).forEach(([bucketName, bucketValue]) => {
          if (!bucketValue || typeof bucketValue !== 'object') return
          const models = Array.isArray(bucketValue?.models) ? bucketValue.models : []
          if (!models.length) return

          const provider = normalizeProvider(bucketName)
          if (!provider) return

          models.forEach((model) => {
            const modelId = String(model?.id || '').trim()
            if (!modelId) return
            const path = String(model?.path || '').trim()
            const basename = path.includes('/') ? path.split('/').filter(Boolean).pop() : ''
            const labelBase = basename && basename !== modelId ? `${modelId} (${basename})` : modelId

            options.push({
              value: `${provider}::${modelId}`,
              provider,
              modelId,
              label: `${labelBase} (${provider})`
            })
          })
        })

        this.modelCatalog = options
        const selectedProvider = String(response?.data?.selected?.provider || '').trim().toLowerCase()
        const selectedModelId = String(response?.data?.selected?.id || response?.data?.selected?.model_id || '').trim()
        const selectedValue = selectedProvider && selectedModelId ? `${selectedProvider}::${selectedModelId}` : ''
        const preferredSelected = selectedValue || this.lastPersistedSelection

        this.selectedModel = preferredSelected && options.some(
          (o) => o.value === preferredSelected)
          ? preferredSelected : options[0]?.value || ''
        this.modelCatalogFetchedAt = Date.now()
        this.lastPersistedSelection = selectedValue || this.lastPersistedSelection

      } catch (error) {
        this.modelCatalogError = 'Unable to load model inventory from /api/v1/ai/models/available. error: ' + (error?.message || 'unknown error')
        this.modelCatalog = []
        this.selectedModel = ''
        this.modelCatalogFetchedAt = 0
      } finally {
        this.modelCatalogLoading = false
      }
    },
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
    async ensureModelCatalogFreshForSession({ staleAfterMs = 300000 } = {}) {
      if (this.modelCatalogLoading) return
      const hasCatalog = this.modelCatalog.length > 0
      const isStale = !this.modelCatalogFetchedAt || (Date.now() - this.modelCatalogFetchedAt) > staleAfterMs
      if (hasCatalog && !isStale) return
      await this.fetchModelCatalog()
    },
    async persistCurrentSelectionIfChanged() {
      const selectedValue = String(this.selectedModel || '').trim()
      if (!selectedValue || !selectedValue.includes('::')) return
      if (selectedValue === this.lastPersistedSelection) return
      await this.updateModelSelection(selectedValue)
    },
    async ensureModelSelectionForSession() {
      await this.ensureModelCatalogFreshForSession()
      await this.persistCurrentSelectionIfChanged()
    },
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
    prepareNewChat() {
      this.selectedChatId = null
      this.newChatRequestId += 1
    },
    async createChat(payload) {
      const tempId = `temp-${Date.now()}`
      const key = `createChat:${tempId}`
      const optimistic = { ...payload, id: tempId }
      this.chats = [...this.chats, optimistic]
      this.selectedChatId = tempId
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: tempId })
      try {
        const response = await api.post('/api/v1/chats', payload)
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
    async updateChat(chatId, patch) {
      const key = `updateChat:${chatId}`
      const snapshot = [...this.chats]
      this.chats = this.chats.map((c) => (c.id === chatId ? { ...c, ...patch } : c))
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
    async ensureActiveChat(payload) {
      const existing = this.chats.find((c) => c.id === this.selectedChatId)
      if (existing) {
        return existing
      }

      const key = 'ensureActiveChat'
      setActionStatus(this.actionStatus, key, {loading: true, error: ''})
      try {
        const response = await api.post('/api/v1/chats', payload)
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
