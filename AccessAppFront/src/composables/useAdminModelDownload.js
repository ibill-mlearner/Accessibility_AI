import { computed, onBeforeUnmount, ref } from 'vue'
import api from '../services/api'

/** Manage admin-triggered model-download requests with cancel/progress UI state. */
export function useAdminModelDownload() {
  // Holds the pending model id entered by the admin in the download form.
  const modelIdInput = ref('')
  // Prevents duplicate submissions while a request is in flight.
  const isSubmitting = ref(false)
  // This is a simple best-effort bar: it only reaches 100% when the backend request actually ends.
  const progressValue = ref(0)
  // Provides human-readable request lifecycle status text.
  const progressStatus = ref('Idle')
  // Tracks the active abort controller so requests can be canceled.
  const submitController = ref(null)
  // Tracks the local timer used for progress simulation increments.
  let progressTimer = null

  // Exposes a trimmed model id value for validation and submit gating.
  const trimmedModelId = computed(() => modelIdInput.value.trim())

  // Stops and clears the progress simulation timer when request state changes.
  function clearProgressTimer() {
    if (progressTimer) {
      globalThis.clearInterval(progressTimer)
      progressTimer = null
    }
  }

  // Starts optimistic progress movement while the backend request is pending.
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

  // Finalizes progress state and displays the terminal status message.
  function finishProgress(message) {
    clearProgressTimer()
    progressValue.value = 100
    progressStatus.value = message
  }

  // Cancels an in-flight admin download request via AbortController.
  function cancelModelDownload() {
    if (!submitController.value) {
      return
    }
    submitController.value.abort()
  }

  // Submits the admin model download request and handles success/cancel/error terminal states.
  async function submitModelDownload() {
    if (!trimmedModelId.value || isSubmitting.value) {
      return
    }

    isSubmitting.value = true
    startProgressSimulation()
    submitController.value = new AbortController()

    try {
      const response = await api.post(
        '/api/v1/admin/model-downloads',
        { model_id: trimmedModelId.value },
        { signal: submitController.value.signal }
      )
      finishProgress(String(response?.data?.message || 'Download request submitted.'))
      modelIdInput.value = ''
    } catch (error) {
      if (error?.code === 'ERR_CANCELED') {
        finishProgress('Download request cancelled.')
      } else {
        finishProgress('Unable to submit download request.')
      }
    } finally {
      submitController.value = null
      isSubmitting.value = false
    }
  }

  onBeforeUnmount(() => {
    clearProgressTimer()
    if (submitController.value) {
      submitController.value.abort()
    }
  })

  return {
    modelIdInput,
    isSubmitting,
    progressValue,
    progressStatus,
    trimmedModelId,
    cancelModelDownload,
    submitModelDownload,
  }
}
