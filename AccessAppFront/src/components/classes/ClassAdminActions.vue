<template>
  <section v-if="canCreate || canDelete" class="card shadow-sm class-admin-actions">
    <div class="card-body d-flex flex-column gap-3">
      <div>
        <h3 class="h5 mb-1">Admin actions</h3>
        <p class="text-muted mb-0">Create new classes or remove an existing class.</p>
      </div>

      <form v-if="canCreate" class="d-flex flex-column gap-2" @submit.prevent="submitCreate">
        <label class="form-label mb-0" for="new-class-name-input">New class name</label>
        <input id="new-class-name-input" v-model="createForm.name" class="form-control" type="text" :disabled="isSubmitting" required>

        <label class="form-label mb-0" for="new-class-description-input">Description</label>
        <textarea
          id="new-class-description-input"
          v-model="createForm.description"
          class="form-control"
          rows="2"
          :disabled="isSubmitting"
        />

        <label class="form-label mb-0" for="new-class-role-input">Role</label>
        <select id="new-class-role-input" v-model="createForm.role" class="form-select" :disabled="isSubmitting">
          <option value="student">Student</option>
          <option value="instructor">Instructor</option>
        </select>

        <button class="btn btn-outline-primary align-self-start" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? 'Creating . . .' : 'Create class' }}
        </button>
      </form>

      <div v-if="canDelete" class="d-flex flex-column gap-2">
        <p class="mb-0"><strong>Delete selected class</strong></p>
        <p v-if="!selectedClass" class="text-muted mb-0">Select a class to delete.</p>
        <button
          class="btn btn-outline-danger align-self-start"
          type="button"
          :disabled="!selectedClass || isSubmitting"
          @click="emitDelete"
        >
          {{ isSubmitting ? 'Working . . .' : 'Delete class' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive } from 'vue'

const props = defineProps({
  selectedClass: { type: Object, default: null },
  canCreate: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
  isSubmitting: { type: Boolean, default: false }
})

const emit = defineEmits(['create', 'delete'])

const createForm = reactive({
  name: '',
  description: '',
  role: 'student'
})

function submitCreate() {
  const name = createForm.name.trim()
  if (!name) return

  emit('create', {
    name,
    description: createForm.description.trim(),
    role: createForm.role
  })

  createForm.name = ''
  createForm.description = ''
  createForm.role = 'student'
}

function emitDelete() {
  if (!props.selectedClass) return
  const confirmed = typeof window === 'undefined'
    ? true
    : window.confirm(`Delete class \"${props.selectedClass.name || props.selectedClass.id}\"?`)
  if (!confirmed) return
  emit('delete', props.selectedClass.id)
}
</script>

<style scoped src="../../styles/components/classes/class-admin-actions.css"></style>
