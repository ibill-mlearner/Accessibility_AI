import { ref } from 'vue'

/** Browser speech-synthesis controls for read-aloud actions in chat UIs. */
export function useSpeechSynthesis() {
  // Resolves browser speech synthesis runtime when available.
  const synthesis = typeof window !== 'undefined' && 'speechSynthesis' in window
    ? speechSynthesis
    : null

  // Flags whether read-aloud APIs are supported in this browser/runtime.
  const isSupported = Boolean(synthesis) && typeof SpeechSynthesisUtterance === 'function'
  // Tracks whether speech output is currently active.
  const isSpeaking = ref(false)
  // Tracks which message row currently owns read-aloud playback.
  const activeReadAloudMessageId = ref(null)
  // Retains current read-aloud text for replay when voice settings change.
  const activeReadAloudText = ref('')
  // Holds current read-aloud volume scalar (0..1).
  const readAloudVolume = ref(1)
  // Holds selected voice name.
  const selectedReadAloudVoice = ref('Samantha')
  // Provides fixed voice options used by current read-aloud controls.
  const readAloudVoiceOptions = [
    { label: 'Samantha', value: 'Samantha' },
    { label: 'Google US English', value: 'Google US English' },
    { label: 'Microsoft Zira - English (United States)', value: 'Microsoft Zira - English (United States)' }
  ]

  // Starts speech playback for given text/voice/volume and updates speaking state callbacks.
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

  // Stops active speech playback and clears speaking state.
  function stop() {
    if (!isSupported) return
    synthesis.cancel()
    isSpeaking.value = false
  }

  // Toggles read-aloud for a message row, including stop-on-repeat behavior.
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

  // Stops read-aloud and clears active message metadata.
  function handleReadAloudStop() {
    if (!isSupported) return
    stop()
    activeReadAloudMessageId.value = null
    activeReadAloudText.value = ''
  }

  // Normalizes and applies requested read-aloud volume.
  function handleReadAloudVolume(nextVolume) {
    const normalizedVolume = Number(nextVolume)
    if (Number.isNaN(normalizedVolume)) return

    readAloudVolume.value = Math.min(1, Math.max(0, normalizedVolume))
  }

  // Applies selected voice and restarts active text playback when already speaking.
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
