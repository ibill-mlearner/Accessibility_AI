import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../lib/actionStatus'
import { toResourceError } from '../lib/apiErrors'

export const useNoteStore = defineStore('notes', {
  state: () => ({
    notes: [],
    actionStatus: {}
  }),
  actions: {
    async fetchNotes() {
      const key = 'fetchNotes'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/notes')
        this.notes = Array.isArray(response?.data) ? response.data : []
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch (error) {
        const wrapped = toResourceError(error, {
          resourceLabel: 'notes',
          unavailableMessage: 'Notes endpoint is unavailable. Enable /api/v1/notes or hide notes functionality.',
          fallbackMessage: 'Unable to load notes.'
        })
        setActionError(this.actionStatus, key, wrapped.message)
        throw wrapped
      }
    },
    async createNote(payload) {
      const tempId = `temp-${Date.now()}`
      const key = `createNote:${tempId}`
      const optimistic = { ...payload, id: tempId }
      this.notes = [...this.notes, optimistic]
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: tempId })
      try {
        const response = await api.post('/api/v1/notes', payload)
        this.notes = this.notes.map((n) => (n.id === tempId ? response.data : n))
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.notes = this.notes.filter((n) => n.id !== tempId)
        setActionError(this.actionStatus, key, 'Unable to create note.')
      }
    },
    async updateNote(noteId, patch) {
      const key = `updateNote:${noteId}`
      const snapshot = [...this.notes]
      this.notes = this.notes.map((n) => (n.id === noteId ? { ...n, ...patch } : n))
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: noteId })
      try {
        const current = this.notes.find((n) => n.id === noteId)
        await api.put(`/api/v1/notes/${noteId}`, current)
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.notes = snapshot
        setActionError(this.actionStatus, key, 'Unable to update note.')
      }
    },
    async deleteNote(noteId) {
      const key = `deleteNote:${noteId}`
      const snapshot = [...this.notes]
      this.notes = this.notes.filter((n) => n.id !== noteId)
      setActionStatus(this.actionStatus, key, { loading: true, error: '', rollbackToken: noteId })
      try {
        await api.delete(`/api/v1/notes/${noteId}`)
        setActionStatus(this.actionStatus, key, { loading: false, error: '', rollbackToken: null })
      } catch {
        this.notes = snapshot
        setActionError(this.actionStatus, key, 'Unable to delete note.')
      }
    }
  }
})