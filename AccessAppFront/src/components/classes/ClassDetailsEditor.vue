<template>
  <section class="card shadow-sm class-details-editor">
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

        <label v-if="isAdmin" class="form-label mb-0" for="class-instructor-input">Instructor email</label>
        <select
          v-if="isAdmin"
          id="class-instructor-input"
          v-model.number="form.instructor_id"
          class="form-select"
          :disabled="!canEdit || isSaving"
          required
        >
          <option :value="null" disabled>Select an instructor</option>
          <option v-for="instructor in instructors" :key="instructor.id" :value="instructor.id">
            {{ instructor.email }}
          </option>
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
  isAdmin: { type: Boolean, default: false },
  instructors: { type: Array, default: () => [] },
  isSaving: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])

const form = reactive({
  name: '',
  description: '',
  instructor_id: null
})

watch(
  () => props.selectedClass,
  (value) => {
    form.name = value?.name || ''
    form.description = value?.description || ''
    form.instructor_id = value?.instructor_id ?? null
  },
  { immediate: true }
)

function submitUpdate() {
  if (!props.selectedClass || !props.canEdit) return
  if (props.isAdmin && !form.instructor_id) return
  emit('save', {
    id: props.selectedClass.id,
    patch: {
      name: form.name.trim(),
      description: form.description.trim(),
      ...(props.isAdmin ? { instructor_id: form.instructor_id } : {})
    }
  })
}
</script>

<style scoped src="../../styles/components/classes/class-details-editor.css"></style>
