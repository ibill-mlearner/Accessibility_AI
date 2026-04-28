import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../stores/helpers/actionStatus'
import { deriveSelectedId } from '../stores/helpers/selection'
import { toResourceError } from '../stores/helpers/apiErrors'

export const useClassStore = defineStore('classes', {
  state: () => ({
    selectedClassId: null,
    classes: [],
    instructors: [],
    actionStatus: {}
  }),
  getters: {
    roleClasses(state) {
      return state.classes
    },
    selectedClass(state) {
      return state.classes.find((c) => c.id === state.selectedClassId) || null
    }
  },
  actions: {
    // This store is intentionally conventional CRUD state management for classes.
    // It keeps request status in one place (`actionStatus`) so the UI can show per-action loading/error feedback
    // while each mutation path updates the list and then reconciles `selectedClassId` to a valid record.
    resetClassState() {
      this.selectedClassId = null
      this.classes = []
      this.instructors = []
      this.actionStatus = {}
    },
    reconcileSelection() {
      this.selectedClassId = deriveSelectedId(this.selectedClassId, this.roleClasses)
    },
    async fetchClasses() {
      const key = 'fetchClasses'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/classes')
        this.classes = Array.isArray(response?.data) ? response.data : []
        this.reconcileSelection()
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch (error) {
        const wrapped = toResourceError(error, {
          resourceLabel: 'classes',
          unavailableMessage: 'Classes endpoint is unavailable. Enable /api/v1/classes or disable class-dependent UI.',
          fallbackMessage: 'Unable to load classes.'
        })
        setActionError(this.actionStatus, key, wrapped.message)
        throw wrapped
      }
    },
    async fetchInstructors() {
      const key = 'fetchInstructors'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.get('/api/v1/classes/instructors')
        this.instructors = Array.isArray(response?.data) ? response.data : []
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch {
        setActionError(this.actionStatus, key, 'Unable to load instructors.')
        throw new Error('Unable to load instructors.')
      }
    },
    async createClass(payload) {
      const key = 'createClass'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.post('/api/v1/classes', payload)
        this.classes = [...this.classes, response.data]
        this.reconcileSelection()
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch {
        setActionError(this.actionStatus, key, 'Unable to create class.')
      }
    },
    async updateClass(classId, patch) {
      const key = `updateClass:${classId}`
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const previous = this.classes.find((c) => c.id === classId) || {}
        const response = await api.put(`/api/v1/classes/${classId}`, { ...previous, ...patch })
        this.classes = this.classes.map((c) => (c.id === classId ? response.data : c))
        this.reconcileSelection()
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch {
        setActionError(this.actionStatus, key, 'Unable to update class.')
      }
    },
    async deleteClass(classId) {
      const key = `deleteClass:${classId}`
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        await api.delete(`/api/v1/classes/${classId}`)
        this.classes = this.classes.filter((c) => c.id !== classId)
        this.reconcileSelection()
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch {
        setActionError(this.actionStatus, key, 'Unable to delete class.')
      }
    },
    setSelectedClassId(classId) {
      this.selectedClassId = classId
      this.reconcileSelection()
    },
    clearSelection() {
      this.selectedClassId = null
    }
  }
})
