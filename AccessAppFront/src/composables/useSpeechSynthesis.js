import { ref } from 'vue'

export function useSpeechSynthesis() {
  const synthesis = typeof window !== 'undefined' && 'speechSynthesis' in window
    ? window.speechSynthesis
    : null

  const isSupported = Boolean(synthesis) && typeof window.SpeechSynthesisUtterance === 'function'
  const isSpeaking = ref(false)

  function start(text, voiceName = 'Samantha', volume = 1) {
    if (!isSupported) return false

    const content = String(text || '').trim()
    if (!content) return false

    synthesis.cancel()

    const utterance = new window.SpeechSynthesisUtterance(content)
    utterance.lang = 'en-US'
    utterance.volume = Math.min(1, Math.max(0, Number(volume) || 0))

    const preferredVoice = synthesis.getVoices().find((voice) => voice.name === voiceName)
    if (preferredVoice) utterance.voice = preferredVoice

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
    if (!isSupported) return
    synthesis.cancel()
    isSpeaking.value = false
  }

  return {
    isSupported,
    isSpeaking,
    start,
    stop
  }
}
