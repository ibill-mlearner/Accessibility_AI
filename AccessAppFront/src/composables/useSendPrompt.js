import { ref } from 'vue'
import { buildFirstChatTitle, createId, readAssistantText, withSingleRetry } from '../utils/helpers'

export function useSendPrompt({ auth, router, chatStore, classStore, timelineMessages, scrollToLatestTurn, interactionError }) {
  const prompt = ref('')
  const interactionLoading = ref(false)

  async function sendPrompt() {
    if (interactionLoading.value) return
    const cleanPrompt = prompt.value.trim()
    if (!cleanPrompt) return

    if (auth.role === 'guest') {
      interactionError.value = 'Please log in to send a prompt.'
      await router.push({ path: '/login', query: { next: '/', prompt: cleanPrompt } })
      return
    }

    const draftPrompt = prompt.value
    const classIdForChat = classStore.selectedClassId || classStore.classes[0]?.id
    if (!classIdForChat) {
      interactionError.value = 'No class is available for this account yet.'
      return
    }

    interactionLoading.value = true
    interactionError.value = ''

    try {
      const ensuredChat = await withSingleRetry(() =>
        chatStore.ensureActiveChat({
          title: buildFirstChatTitle(cleanPrompt, chatStore.chats.length + 1),
          started_at: new Date().toISOString(),
          model: chatStore.selectedModel || 'General',
          class_id: classIdForChat,
          user_id: auth.currentUser?.id
        })
      )

      const userMessage = await withSingleRetry(() =>
        chatStore.createMessage({ id: createId(), chat_id: ensuredChat.id, message_text: cleanPrompt, help_intent: 'summarization' })
      )
      timelineMessages.value.push({ id: userMessage.id, role: 'user', text: userMessage.message_text })
      await scrollToLatestTurn()

      let aiResponse
      try {
        aiResponse = await chatStore.requestAiInteraction({
          prompt: cleanPrompt,
          chat_id: ensuredChat.id,
          context: { chat_id: ensuredChat.id, class_id: classIdForChat, messages: [{ role: 'user', content: cleanPrompt }] }
        })
      } catch (error) {
        interactionError.value = error?.response?.status === 400 ? 'Prompt was rejected. Please edit and retry.' : 'AI is temporarily unavailable. Please retry.'
        prompt.value = draftPrompt
        return
      }

      const assistantText = readAssistantText(aiResponse)
      if (!assistantText) {
        interactionError.value = 'Assistant response was not in a usable format. Please retry.'
        prompt.value = draftPrompt
        return
      }

      const pendingAssistantId = `assistant-unsaved-${createId()}`
      timelineMessages.value.push({ id: pendingAssistantId, role: 'assistant', text: assistantText, unsaved: true })
      await scrollToLatestTurn()

      const savedAssistantMessage = await withSingleRetry(() =>
        chatStore.createMessage({ id: createId(), chat_id: ensuredChat.id, message_text: assistantText, help_intent: 'summarization' })
      )

      timelineMessages.value = timelineMessages.value.map((message) =>
        message.id === pendingAssistantId ? { id: savedAssistantMessage.id, role: 'assistant', text: savedAssistantMessage.message_text } : message
      )
      await scrollToLatestTurn()
      prompt.value = ''
    } catch (error) {
      const storeMessage = error?.message || ''
      interactionError.value = storeMessage.includes('start chat')
        ? 'Couldn’t start chat. Please retry.'
        : storeMessage.includes('save message')
          ? timelineMessages.value.some((message) => message.unsaved)
            ? 'Response generated but couldn’t be saved. Retry save?'
            : 'Message not saved. Retry sending?'
          : 'Something went wrong. Please retry.'
      prompt.value = draftPrompt
    } finally {
      interactionLoading.value = false
    }
  }

  return { prompt, interactionLoading, sendPrompt }
}