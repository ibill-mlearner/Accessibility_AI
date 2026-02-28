import { nextTick, ref } from 'vue'

export function useAutoScroll() {
  const messageListRef = ref(null)

  async function scrollToLatestTurn() {
    await nextTick()
    if (!messageListRef.value) return
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }

  return { messageListRef, scrollToLatestTurn }
}