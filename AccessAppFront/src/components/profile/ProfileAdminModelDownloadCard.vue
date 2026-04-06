<template>
  <section class="card shadow-sm profile-admin-model-download-card">
    <div class="card-body d-flex flex-column gap-3">
      <div>
        <h3 class="h6 text-uppercase text-muted mb-1">Model downloads</h3>
        <p class="mb-0 text-muted small">
          Queue a model download for the AI pipeline inventory.
        </p>
      </div>

      <form class="d-flex flex-column gap-2" @submit.prevent="submitModelDownload">
        <label class="form-label mb-0" for="admin-model-id-input">Model ID</label>
        <input
          id="admin-model-id-input"
          v-model="modelIdInput"
          class="form-control"
          type="text"
          placeholder="e.g. meta-llama/Llama-3.1-8B-Instruct"
          :disabled="isSubmitting"
          required
        >

        <button class="btn btn-outline-primary align-self-start" type="submit" :disabled="isSubmitting || !trimmedModelId">
          {{ isSubmitting ? 'Submitting . . .' : 'Download model' }}
        </button>
      </form>

      <div class="d-flex flex-column gap-1" aria-live="polite">
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-muted small">Progress</span>
          <span class="small fw-semibold">{{ progressValue }}%</span>
        </div>
        <div class="progress" role="progressbar" aria-label="Model download progress" :aria-valuenow="progressValue" aria-valuemin="0" aria-valuemax="100">
          <div
            class="progress-bar progress-bar-striped"
            :class="{ 'progress-bar-animated': isSubmitting }"
            :style="{ width: `${progressValue}%` }"
          />
        </div>
        <p class="mb-0 text-muted small">{{ progressStatus }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const emit = defineEmits(['submit'])

const modelIdInput = ref('')
const isSubmitting = ref(false)
const progressValue = ref(0)
const progressStatus = ref('Idle')
let progressTimer = null

const trimmedModelId = computed(() => modelIdInput.value.trim())

function clearProgressTimer() {
  if (progressTimer) {
    globalThis.clearInterval(progressTimer)
    progressTimer = null
  }
}

function startProgressSimulation() {
  clearProgressTimer()
  progressValue.value = 10
  progressStatus.value = 'Submitting request . . .'

  progressTimer = globalThis.setInterval(() => {
    if (progressValue.value >= 90) {
      clearProgressTimer()
      return
    }
    progressValue.value += 10
  }, 300)
}

function finishProgress(message) {
  clearProgressTimer()
  progressValue.value = 100
  progressStatus.value = message
}

async function submitModelDownload() {
  if (!trimmedModelId.value || isSubmitting.value) {
    return
  }

  isSubmitting.value = true
  startProgressSimulation()

  try {
    await emit('submit', trimmedModelId.value)
    finishProgress('Download request submitted.')
    modelIdInput.value = ''
  } catch {
    finishProgress('Unable to submit download request.')
  } finally {
    isSubmitting.value = false
  }
}

onBeforeUnmount(() => {
  clearProgressTimer()
})
</script>

<style scoped src="../../styles/components/profile/profile-admin-model-download-card.css"></style>
