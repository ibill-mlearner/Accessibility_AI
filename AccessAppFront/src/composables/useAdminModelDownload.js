import { computed, onBeforeUnmount, ref } from 'vue'
import api from '../services/api'

export function useAdminModelDownload() {
  const modelIdInput = ref('')
  const isSubmitting = ref(false)
  const progressValue = ref(0)
  const progressStatus = ref('Idle')
  const submitController = ref(null)
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

  function cancelModelDownload() {
    if (!submitController.value) {
      return
    }
    submitController.value.abort()
  }

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
