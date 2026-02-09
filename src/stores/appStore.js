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
          api.get('/chats'),
          api.get('/classes'),
          api.get('/notes'),
          api.get('/features')
        ])
        this.chats = chats.data
        this.classes = classes.data
        this.notes = notes.data
        this.features = features.data
        this.selectedChatId = this.chats[0]?.id || null
      } catch (error) {
        this.error = 'Unable to load mock API data. Is json-server running?'
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
