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
