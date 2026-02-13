import { defineStore } from 'pinia'
import api from '../services/api'

export const useAppStore = defineStore('app', {
  state: () => ({
    role: 'guest',
    selectedChatId: null,
    selectedClassId: null,
    selectedModel: '',
    chats: [],
    classes: [],
    notes: [],
    features: [],
    loading: false,
    error: ''
  }),
  getters: {
    topHeader(state) {
      return state.role === 'guest'
        ? 'Not logged in, current chat does not save'
        : 'Model Selected     Class selected'
    },
    roleClasses(state) {
      if (state.role === 'guest') return []
      return state.classes.filter((item) => item.role === state.role)
    }
  },
  actions: {
    async bootstrap() {
      this.loading = true
      this.error = ''
      try {
        const [chats, classes, notes, features] = await Promise.all([
          api.get('/api/v1/chats'),
          api.get('/api/v1/classes'),
          api.get('/api/v1/notes'),
          api.get('/api/v1/features')
        ])
        this.chats = chats.data
        this.classes = classes.data
        this.notes = notes.data
        this.features = features.data
        this.selectedChatId = this.chats[0]?.id || null
      } catch (error) {
        this.error = 'Unable to load data from the backend service. Please try again.'
      } finally {
        this.loading = false
      }
    },
    login() {
      this.role = 'student'
    },
    logout() {
      this.role = 'guest'
      this.selectedClassId = null
    },
    setRole(role) {
      this.role = role
      this.selectedClassId = null
    }
  }
})
