import { computed, onMounted, watch } from 'vue'

const allowedRoles = ['student', 'instructor', 'admin']

function normalizeRole(roleLike) {
  const normalized = String(roleLike || '').toLowerCase()
  return allowedRoles.includes(normalized) ? normalized : 'student'
}

export function useClassesViewState({ auth, classStore }) {


  const normalizedRole = computed(() => normalizeRole(auth.role))
  const allowedActions = computed(() => new Set(auth.allowedActions || []))
  const canEditClass = computed(() =>
    (normalizedRole.value === 'instructor' || normalizedRole.value === 'admin')
    && allowedActions.value.has('classes:write')
  )
  const canCreateClass = computed(() =>
    normalizedRole.value === 'admin' && allowedActions.value.has('classes:write')
  )
  const canDeleteClass = computed(() =>
    normalizedRole.value === 'admin' && allowedActions.value.has('classes:delete')
  )

// const canEditClass = computed(() => normalizedRole.value === 'instructor' || normalizedRole.value === 'admin')
// const canCreateClass = computed(() => normalizedRole.value === 'admin')
// const canDeleteClass = computed(() => normalizedRole.value === 'admin')

  const roleSummary = computed(() => {
    if (normalizedRole.value === 'admin') return 'Admin access: create, update, and delete classes.'
    if (normalizedRole.value === 'instructor') return 'Instructor access: update class details.'
    return 'Student access: view and select classes.'
  })

  const fetchLoading = computed(() => Boolean(classStore.actionStatus?.fetchClasses?.loading))
  const fetchError = computed(() => classStore.actionStatus?.fetchClasses?.error || '')

  const updateActionKey = computed(() => `updateClass:${classStore.selectedClassId}`)
  const updateLoading = computed(() => Boolean(classStore.actionStatus?.[updateActionKey.value]?.loading))
  const updateError = computed(() => classStore.actionStatus?.[updateActionKey.value]?.error || '')

  const deleteActionKey = computed(() => `deleteClass:${classStore.selectedClassId}`)
  const deleteLoading = computed(() => Boolean(classStore.actionStatus?.[deleteActionKey.value]?.loading))
  const deleteError = computed(() => classStore.actionStatus?.[deleteActionKey.value]?.error || '')

  const createLoading = computed(() => Boolean(classStore.actionStatus?.createClass?.loading))
  const createError = computed(() => classStore.actionStatus?.createClass?.error || '')

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

  // watch(
  //   () => props.role || route.params.role,
  //   (value) => {
  //     const paramRole = normalizeRole(value)
  //     if (!auth.isAuthenticated) return
  //     if (auth.role === 'admin') return
  //     if (paramRole !== auth.role) {
  //       auth.setRole(paramRole)
  //     }
  //   },
  //   { immediate: true }
  // )

  async function handleCreateClass(payload) {
    if (!canCreateClass.value) return
    await classStore.createClass(payload)
  }

  async function handleUpdateClass({ id, patch }) {
    if (!canEditClass.value || !id) return
    await classStore.updateClass(id, patch)
  }

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
