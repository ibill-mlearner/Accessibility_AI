import { ref } from 'vue'

export function useSpeechSynthesis() {
  const synthesis = typeof window !== 'undefined' && 'speechSynthesis' in window
    ? window.speechSynthesis
    : null

  const isSpeaking = ref(false)
  const lastPlaceholderIndex = ref(-1)

  function resolveTextToSpeak(text, placeholder = '') {
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

  function resolveVoiceName(voiceName = 'Samantha') {
    return synthesis.getVoices().find((voice) => voice.name === voiceName)
  }

  const resolveVolume = (volume = 1) => volume

  function start(text, placeholder = '', voiceName = 'Samantha', volume = 1) {
    if (!synthesis) return false

    const content = resolveTextToSpeak(text, placeholder)
    if (!content) return false

    synthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(content)
    utterance.lang = 'en-US'
    utterance.volume = resolveVolume(volume)
    const preferredVoice = resolveVoiceName(voiceName)
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
    if (!synthesis) return
    synthesis.cancel()
    isSpeaking.value = false
  }

  return {
    isSpeaking,
    lastPlaceholderIndex,
    resolveVolume,
    resolveVoiceName,
    start,
    stop
  }
}
