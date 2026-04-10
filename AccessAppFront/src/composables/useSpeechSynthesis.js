import { ref } from 'vue'

const DEFAULT_PLACEHOLDER = ''

export function useSpeechSynthesis() {
  const synthesis = typeof window !== 'undefined' && 'speechSynthesis' in window
    ? window.speechSynthesis
    : null

  const isSpeaking = ref(false)
  const lastPlaceholderIndex = ref(-1)

  function resolveTextToSpeak(text, placeholder = DEFAULT_PLACEHOLDER) {
    const content = String(text || '')
    const marker = String(placeholder || '').trim()

    if (!marker) {
      lastPlaceholderIndex.value = -1
      return ''
    }

    const markerIndex = content.indexOf(marker)
    lastPlaceholderIndex.value = markerIndex

    if (markerIndex === -1) return ''

    return content.slice(markerIndex + marker.length).trim()
  }

  function start(text, placeholder = DEFAULT_PLACEHOLDER) {
    if (!synthesis) return false

    const content = resolveTextToSpeak(text, placeholder)
    if (!content) return false

    synthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(content)
    utterance.lang = 'en-US'

    utterance.onstart = () => {
      isSpeaking.value = true
    }

    utterance.onend = () => {
      isSpeaking.value = false
    }

    utterance.onerror = () => {
      isSpeaking.value = false
    }

    synthesis.speak(utterance)
    return true
  }

  function stop() {
    if (!synthesis) return
    synthesis.cancel()
    isSpeaking.value = false
  }

  return {
    isSpeaking,
    lastPlaceholderIndex,
    start,
    stop
  }
}
