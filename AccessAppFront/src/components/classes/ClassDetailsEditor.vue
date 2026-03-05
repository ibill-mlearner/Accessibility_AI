<template>
  <section class="card shadow-sm">
    <div class="card-body d-flex flex-column gap-3">
      <div>
        <h3 class="h5 mb-1">Edit class details</h3>
        <p class="text-muted mb-0">Update the selected class metadata.</p>
      </div>

      <p v-if="!selectedClass" class="mb-0 text-muted">Select a class to edit details.</p>

      <form v-else class="d-flex flex-column gap-2" @submit.prevent="submitUpdate">
        <label class="form-label mb-0" for="class-name-input">Name</label>
        <input id="class-name-input" v-model="form.name" class="form-control" type="text" :disabled="!canEdit || isSaving" required>

        <label class="form-label mb-0" for="class-description-input">Description</label>
        <textarea
          id="class-description-input"
          v-model="form.description"
          class="form-control"
          rows="3"
          :disabled="!canEdit || isSaving"
        />

        <label class="form-label mb-0" for="class-role-input">Role</label>
        <select id="class-role-input" v-model="form.role" class="form-select" :disabled="!canEdit || isSaving">
          <option value="student">Student</option>
          <option value="instructor">Instructor</option>
        </select>

        <button class="btn btn-primary align-self-start" type="submit" :disabled="!canEdit || isSaving">
          {{ isSaving ? 'Saving . . .' : 'Save details' }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  selectedClass: { type: Object, default: null },
  canEdit: { type: Boolean, default: false },
  isSaving: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])

const form = reactive({
  name: '',
  description: '',
  role: 'student'
})

watch(
  () => props.selectedClass,
  (value) => {
    form.name = value?.name || ''
    form.description = value?.description || ''
    form.role = value?.role || 'student'
  },
  { immediate: true }
)

function submitUpdate() {
  if (!props.selectedClass || !props.canEdit) return
  emit('save', {
    id: props.selectedClass.id,
    patch: {
      name: form.name.trim(),
      description: form.description.trim(),
      role: form.role
    }
  })
}
</script>
