import { ref } from 'vue'
import { normalizeTimeline } from '../../utils/timeline'

export function useChatTimeline(chatStore) {
  const timelineMessages = ref([])
  const interactionError = ref('')
  const timelineLoadRequestId = ref(0)

  async function hydrateTimelineForChat(chatId) {
    if (!chatId) {
      timelineMessages.value = []
      return
    }

    const requestId = timelineLoadRequestId.value + 1
    timelineLoadRequestId.value = requestId

    try {
      const [interactions, messages] = await Promise.all([
        chatStore.fetchChatInteractions(chatId),
        chatStore.fetchChatMessages(chatId)
      ])
      if (timelineLoadRequestId.value !== requestId) return
      timelineMessages.value = normalizeTimeline(interactions, messages)
    } catch {
      if (timelineLoadRequestId.value !== requestId) return
      interactionError.value = 'Unable to load chat history right now.'
    }
  }

  return { timelineMessages, interactionError, hydrateTimelineForChat }
}