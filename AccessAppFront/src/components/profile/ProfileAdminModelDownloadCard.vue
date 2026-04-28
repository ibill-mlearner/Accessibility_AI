<template>
  <section class="card shadow-sm profile-admin-model-download-card">
    <div class="card-body d-flex flex-column gap-3">
      <div>
        <h3 class="h6 text-uppercase text-muted mb-1">Model downloads</h3>
        <p class="mb-0 text-muted small">
          Queue a model download for the AI pipeline inventory.
        </p>
        <p class="mb-0 mt-2 text-muted small">Suggested Hugging Face models:</p>
        <ul class="mb-0 text-muted small ps-3">
          <li>3B: Qwen/Qwen2.5-3B-Instruct</li>
          <li>1.5B: Qwen/Qwen2.5-1.5B-Instruct</li>
          <li>500M: Qwen/Qwen2.5-0.5B-Instruct</li>
        </ul>
      </div>

      <form class="d-flex flex-column gap-2" @submit.prevent="submitModelDownload">
        <label class="form-label mb-0" for="admin-model-id-input">Model ID</label>
        <input
          id="admin-model-id-input"
          v-model="modelIdInput"
          class="form-control"
          type="text"
          placeholder="e.g. Qwen/Qwen2.5-0.5B-Instruct"
          :disabled="isSubmitting"
          required
        >

        <div class="d-flex align-items-center gap-2">
          <button class="btn btn-outline-primary" type="submit" :disabled="isSubmitting || !trimmedModelId">
            {{ isSubmitting ? 'Submitting . . .' : 'Download model' }}
          </button>
          <button v-if="isSubmitting" class="btn btn-outline-secondary" type="button" @click="cancelModelDownload">
            Cancel
          </button>
        </div>
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
import { useAdminModelDownload } from '../../composables/useAdminModelDownload'

const {
  modelIdInput,
  isSubmitting,
  progressValue,
  progressStatus,
  trimmedModelId,
  cancelModelDownload,
  submitModelDownload,
} = useAdminModelDownload()
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/profile/profile-admin-model-download-card.css"></style>
