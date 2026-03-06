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
      this.newChatRequestId = 0
      this.chats = []
      this.actionStatus = {}
    },
    async fetchModelCatalog() {
      this.modelCatalogLoading = true
      this.modelCatalogError = ''
      try {
        const response = await api.get('/api/v1/ai/catalog')
        const families = Array.isArray(response?.data?.families) ? response.data.families : []
        const options = []

        families.forEach((f) => {
          const models = Array.isArray(f?.models) ? f.models : []
          models.forEach((m) => {
            if (!m?.available) return
            const provider = String(m?.provider || '').trim().toLowerCase()
            const modelId = String(m?.model_id || '').trim()
            if (!provider || !modelId) return
            options.push({
              value: `${provider}::${modelId}`,
              provider,
              modelId,
              label: `${f?.label || modelId} (${provider})`
            })
          })
        })

        this.modelCatalog = options
        const selectedProvider = String(response?.data?.selected?.provider || '').trim().toLowerCase()
        const selectedModelId = String(response?.data?.selected?.model_id || '').trim()
        const selectedValue = selectedProvider && selectedModelId ? `${selectedProvider}::${selectedModelId}` : ''

        this.selectedModel = selectedValue && options.some(
          (o) => o.value === selectedValue) 
          ? selectedValue : options[0]?.value || ''

      } catch (error) {
        this.modelCatalogError = 'Unable to load model catalog. error: ' + (error?.message || 'unknown error')
        this.modelCatalog = []
        this.selectedModel = ''
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
        const persistedModelId = String(response?.data?.model_id || modelId).trim()
        this.selectedModel = `${persistedProvider}::${persistedModelId}`
      } catch {
        this.modelCatalogError = 'Unable to update model selection. Please try again.'
      }
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