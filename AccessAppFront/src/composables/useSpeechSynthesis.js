import { ref } from 'vue'

export function useSpeechSynthesis() {
  const synthesis = typeof window !== 'undefined' && 'speechSynthesis' in window
    ? speechSynthesis
    : null

  const isSupported = Boolean(synthesis) && typeof SpeechSynthesisUtterance === 'function'
  const isSpeaking = ref(false)
  const activeReadAloudMessageId = ref(null)
  const activeReadAloudText = ref('')
  const readAloudVolume = ref(1)
  const selectedReadAloudVoice = ref('Samantha')
  const readAloudVoiceOptions = [
    { label: 'Samantha', value: 'Samantha' },
    { label: 'Google US English', value: 'Google US English' },
    { label: 'Microsoft Zira - English (United States)', value: 'Microsoft Zira - English (United States)' }
  ]

  function start(text, voiceName = 'Samantha', volume = 1) {
    if (!isSupported) return false

    const content = String(text || '').trim()
    if (!content) return false

    synthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(content)
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

  function handleReadAloudToggle(message) {
    if (!isSupported || !message?.text?.trim()) return

    const isSameMessage = activeReadAloudMessageId.value === message.id
    if (isSameMessage && isSpeaking.value) {
      handleReadAloudStop()
      return
    }

    start(message.text, selectedReadAloudVoice.value, readAloudVolume.value)
    activeReadAloudMessageId.value = message.id
    activeReadAloudText.value = message.text
  }

  function handleReadAloudStop() {
    if (!isSupported) return
    stop()
    activeReadAloudMessageId.value = null
    activeReadAloudText.value = ''
  }

  function handleReadAloudVolume(nextVolume) {
    const normalizedVolume = Number(nextVolume)
    if (Number.isNaN(normalizedVolume)) return

    readAloudVolume.value = Math.min(1, Math.max(0, normalizedVolume))
  }

  function handleReadAloudVoice(nextVoiceName) {
    selectedReadAloudVoice.value = String(nextVoiceName || '').trim() || 'Samantha'

    if (!isSpeaking.value || !activeReadAloudText.value) return

    start(activeReadAloudText.value, selectedReadAloudVoice.value, readAloudVolume.value)
  }

  return {
    isSupported,
    isSpeaking,
    activeReadAloudMessageId,
    readAloudVolume,
    selectedReadAloudVoice,
    readAloudVoiceOptions,
    start,
    stop,
    handleReadAloudToggle,
    handleReadAloudStop,
    handleReadAloudVolume,
    handleReadAloudVoice
  }
}
