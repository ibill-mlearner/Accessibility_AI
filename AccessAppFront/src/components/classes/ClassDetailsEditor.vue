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

        <button class="btn btn-primary align-self-start" type="submit" :disabled="!canEdit || isSaving">
          {{ isSaving ? 'Saving . . .' : 'Save details' }}
        </button>

        <div v-if="canDelete" class="d-flex flex-column gap-2 pt-2">
          <p class="mb-0"><strong>Delete selected class</strong></p>
          <button
            class="btn btn-outline-danger align-self-start"
            type="button"
            :disabled="!selectedClass || isDeleting"
            @click="emitDelete"
          >
            {{ isDeleting ? 'Working . . .' : 'Delete class' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  selectedClass: { type: Object, default: null },
  canEdit: { type: Boolean, default: false },
  isSaving: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
  isDeleting: { type: Boolean, default: false }
})

const emit = defineEmits(['save', 'delete'])

const form = reactive({
  name: '',
  description: ''
})

watch(
  () => props.selectedClass,
  (value) => {
    form.name = value?.name || ''
    form.description = value?.description || ''
  },
  { immediate: true }
)

function submitUpdate() {
  if (!props.selectedClass || !props.canEdit) return
  emit('save', {
    id: props.selectedClass.id,
    patch: {
      name: form.name.trim(),
      description: form.description.trim()
    }
  })
}

function emitDelete() {
  if (!props.selectedClass || !props.canDelete) return
  const confirmed = typeof window === 'undefined'
    ? true
    : window.confirm(`Delete class \"${props.selectedClass.name || props.selectedClass.id}\"?`)
  if (!confirmed) return
  emit('delete', props.selectedClass.id)
}
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/classes/class-details-editor.css"></style>
