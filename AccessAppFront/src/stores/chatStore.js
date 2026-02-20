import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../stores/helpers/actionStatus'
import { deriveSelectedId } from '../stores/helpers/selection'
import { toResourceError } from '../stores/helpers/apiErrors'

export const useChatStore = defineStore('chats', {
  state: () => ({
    selectedChatId: null,
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