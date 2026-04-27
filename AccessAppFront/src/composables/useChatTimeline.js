import { ref } from 'vue'
import { normalizeTimeline } from '../utils/timeline'

/** Load and normalize merged interaction/message history for one selected chat. */
export function useChatTimeline(chatStore) {
  // Stores the merged, UI-ready timeline rows rendered in the chat transcript.
  const timelineMessages = ref([])
  // Carries a user-facing timeline load failure message for the current chat context.
  const interactionError = ref('')
  // Guards against out-of-order async responses when users switch chats quickly.
  const timelineLoadRequestId = ref(0)

  // Fetches interactions/messages concurrently and only applies the latest request result.
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
