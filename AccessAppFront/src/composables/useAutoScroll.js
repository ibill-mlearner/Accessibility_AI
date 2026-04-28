import { nextTick, ref } from 'vue'

/** Keep chat transcript pinned to the newest turn after message mutations. */
export function useAutoScroll() {
  // Provides the DOM element handle for the scrollable message list container.
  const messageListRef = ref(null)

  // Scrolls to the bottom after Vue DOM flush so new messages in the current chat stay visible.
  async function scrollToLatestTurn() {
    await nextTick()
    if (!messageListRef.value) return
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }

  return { messageListRef, scrollToLatestTurn }
}
