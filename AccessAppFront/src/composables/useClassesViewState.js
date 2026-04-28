import { computed, onMounted, watch } from 'vue'

const allowedRoles = ['student', 'instructor', 'admin']

function normalizeRole(roleLike) {
  const normalized = String(roleLike || '').toLowerCase()
  return allowedRoles.includes(normalized) ? normalized : 'student'
}

/** Centralize role/capability and async-status state for the classes view container. */
export function useClassesViewState({ auth, classStore }) {
  // Normalizes incoming role labels so downstream capability checks stay deterministic.
  const normalizedRole = computed(() => normalizeRole(auth.role))
  // Converts allowed actions into a set for fast capability lookups.
  const allowedActions = computed(() => new Set(auth.allowedActions || []))
  // Enables class-detail editing for instructor/admin roles with write capability.
  const canEditClass = computed(() =>
    (normalizedRole.value === 'instructor' || normalizedRole.value === 'admin')
    && allowedActions.value.has('classes:write')
  )
  // Enables class creation for admins that can write classes.
  const canCreateClass = computed(() =>
    normalizedRole.value === 'admin' && allowedActions.value.has('classes:write')
  )
  // Enables class deletion for admins with explicit delete capability.
  const canDeleteClass = computed(() =>
    normalizedRole.value === 'admin' && allowedActions.value.has('classes:delete')
  )

  // Builds a single role summary line for top-level view messaging.
  const roleSummary = computed(() => {
    if (normalizedRole.value === 'admin') return 'Admin access: create, update, and delete classes.'
    if (normalizedRole.value === 'instructor') return 'Instructor access: update class details.'
    return 'Student access: view and select classes.'
  })

  // Tracks classes fetch loading state for initial/refresh UI spinners.
  const fetchLoading = computed(() => Boolean(classStore.actionStatus?.fetchClasses?.loading))
  // Tracks classes fetch errors for route-level feedback.
  const fetchError = computed(() => classStore.actionStatus?.fetchClasses?.error || '')

  // Resolves the update action key for the currently selected class.
  const updateActionKey = computed(() => `updateClass:${classStore.selectedClassId}`)
  // Tracks selected-class update loading state for editor controls.
  const updateLoading = computed(() => Boolean(classStore.actionStatus?.[updateActionKey.value]?.loading))
  // Tracks selected-class update errors for editor feedback.
  const updateError = computed(() => classStore.actionStatus?.[updateActionKey.value]?.error || '')

  // Resolves the delete action key for the currently selected class.
  const deleteActionKey = computed(() => `deleteClass:${classStore.selectedClassId}`)
  // Tracks selected-class delete loading state.
  const deleteLoading = computed(() => Boolean(classStore.actionStatus?.[deleteActionKey.value]?.loading))
  // Tracks selected-class delete errors.
  const deleteError = computed(() => classStore.actionStatus?.[deleteActionKey.value]?.error || '')

  // Tracks admin class-creation loading state.
  const createLoading = computed(() => Boolean(classStore.actionStatus?.createClass?.loading))
  // Tracks admin class-creation errors.
  const createError = computed(() => classStore.actionStatus?.createClass?.error || '')

  // Hydrates classes on first mount and preloads instructor options for admin create flow.
  onMounted(async () => {
    if (!classStore.classes.length) {
      await classStore.fetchClasses()
    } else {
      classStore.reconcileSelection()
    }
    if (canCreateClass.value) {
      await classStore.fetchInstructors()
    }
  })

  // Delegates class creation while enforcing role/capability gates.
  async function handleCreateClass(payload) {
    if (!canCreateClass.value) return
    await classStore.createClass(payload)
  }

  // Delegates class updates while enforcing edit capability and valid target id.
  async function handleUpdateClass({ id, patch }) {
    if (!canEditClass.value || !id) return
    await classStore.updateClass(id, patch)
  }

  // Delegates class deletion while enforcing delete capability and valid target id.
  async function handleDeleteClass(classId) {
    if (!canDeleteClass.value || !classId) return
    await classStore.deleteClass(classId)
  }

  return {
    canEditClass,
    canCreateClass,
    canDeleteClass,
    roleSummary,
    fetchLoading,
    fetchError,
    updateLoading,
    updateError,
    deleteLoading,
    deleteError,
    createLoading,
    createError,
    handleCreateClass,
    handleUpdateClass,
    handleDeleteClass
  }
}
