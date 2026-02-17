<template>
  <section class="chat-thread">
    <div ref="messageListRef" class="chat-messages" aria-live="polite">
      <div class="chat-thread__messages">
        <p v-if="interactionError" class="chat-error-banner">{{ interactionError }}</p>
        <p v-if="interactionLoading" class="chat-loading-banner">Sending…</p>
        <template v-if="store.role !== 'guest'">
          <ChatBubbleCard
            v-for="message in conversationMessages"
            :key="message.id"
            :text="message.text"
            :variant="messageVariantMap[message.role] || message.role"
            :show-actions="message.role === 'assistant'"
            @save-note="saveCurrentChatAsNote"
          />
        </template>
      </div>
    </div>
    <ComposerBar
      v-model="prompt"
      :selected-model="store.selectedModel"
      :show-login="store.role === 'guest'"
      @login="router.push('/login')"
      @send="sendPrompt"
      @update:selected-model="store.selectedModel = $event"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'
import ChatBubbleCard from '../components/chat/ChatBubbleCard.vue'
import ComposerBar from '../components/chat/ComposerBar.vue'

const router = useRouter()
const route = useRoute()
const store = useAppStore()
const prompt = ref('')
const interactionLoading = ref(false)
const interactionError = ref('')
const timelineMessages = ref([])
const messageListRef = ref(null)

const selectedChat = computed(() => store.chats.find((chat) => chat.id === store.selectedChatId) || null)
const activeChatText = computed(() => {
  if (!selectedChat.value) return "System's response . . ."
  return selectedChat.value.title || "System's response . . ."
})
const promptPreviewText = computed(() => prompt.value || "User's prompt . . .")

const messageVariantMap = {
  assistant: 'system',
  system: 'system',
  user: 'user'
}

const conversationMessages = computed(() => {
  if (timelineMessages.value.length) {
    return timelineMessages.value.map((message) => ({
      ...message,
      text: message.unsaved ? `${message.text} (unsaved)` : message.text
    }))
  }

  return [
    {
      id: selectedChat.value?.id ?? 'assistant-preview',
      role: 'assistant',
      text: activeChatText.value
    },
    {
      id: 'user-preview',
      role: 'user',
      text: promptPreviewText.value
    }
  ]
})

function createId() {
  return Date.now() + Math.floor(Math.random() * 1000)
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function withSingleRetry(task) {
  try {
    return await task()
  } catch {
    await wait(350)
    return task()
  }
}

function readAssistantText(aiPayload) {
  if (aiPayload?.response?.summary) return aiPayload.response.summary
  if (typeof aiPayload?.response === 'string' && aiPayload.response.trim()) return aiPayload.response
  if (typeof aiPayload?.summary === 'string' && aiPayload.summary.trim()) return aiPayload.summary
  if (typeof aiPayload === 'string' && aiPayload.trim()) return aiPayload
  try {
    return JSON.stringify(aiPayload)
  } catch {
    return 'Assistant response unavailable.'
  }
}

async function sendPrompt() {
  if (interactionLoading.value) return

  const cleanPrompt = prompt.value.trim()
  if (!cleanPrompt) return

  if (store.role === 'guest') {
    interactionError.value = 'Please log in to send a prompt.'
    await router.push({ path: '/login', query: { next: '/', prompt: cleanPrompt } })
    return
  }

  const draftPrompt = prompt.value
  interactionLoading.value = true
  interactionError.value = ''

  const messageIntent = 'summarization'

  try {
    const ensuredChat = await withSingleRetry(() =>
      store.ensureActiveChat({
        id: createId(),
        title: cleanPrompt.slice(0, 60),
        start: new Date().toISOString(),
        model: store.selectedModel || 'General',
        class: store.selectedClass?.name || '',
        user: store.role
      })
    )

    const userMessage = await withSingleRetry(() =>
      store.createMessage({
        id: createId(),
        chat_id: ensuredChat.id,
        message_text: cleanPrompt,
        help_intent: messageIntent
      })
    )
    timelineMessages.value.push({ id: userMessage.id, role: 'user', text: userMessage.message_text })
    await scrollToLatestTurn()

    let aiResponse
    try {
      aiResponse = await store.requestAiInteraction({ prompt: cleanPrompt })
    } catch (error) {
      const status = error?.response?.status
      interactionError.value =
        status === 400
          ? 'Prompt was rejected. Please edit and retry.'
          : 'AI is temporarily unavailable. Please retry.'
      prompt.value = draftPrompt
      return
    }

    const assistantText = readAssistantText(aiResponse)
    const pendingAssistantId = `assistant-unsaved-${createId()}`
    timelineMessages.value.push({ id: pendingAssistantId, role: 'assistant', text: assistantText, unsaved: true })
    await scrollToLatestTurn()

    const savedAssistantMessage = await withSingleRetry(() =>
      store.createMessage({
        id: createId(),
        chat_id: ensuredChat.id,
        message_text: assistantText,
        help_intent: messageIntent
      })
    )

    timelineMessages.value = timelineMessages.value.map((message) =>
      message.id === pendingAssistantId
        ? { id: savedAssistantMessage.id, role: 'assistant', text: savedAssistantMessage.message_text }
        : message
    )
    await scrollToLatestTurn()

    prompt.value = ''
  } catch (error) {
    const storeMessage = error?.message || ''
    if (storeMessage.includes('start chat')) {
      interactionError.value = "Couldn’t start chat. Please retry."
    } else if (storeMessage.includes('save message')) {
      if (!timelineMessages.value.some((message) => message.unsaved)) {
        interactionError.value = 'Message not saved. Retry sending?'
      } else {
        interactionError.value = 'Response generated but couldn’t be saved. Retry save?'
      }
    } else {
      interactionError.value = 'Something went wrong. Please retry.'
    }
    prompt.value = draftPrompt
  } finally {
    interactionLoading.value = false
  }
}

async function scrollToLatestTurn() {
  await nextTick()
  if (!messageListRef.value) return
  messageListRef.value.scrollTop = messageListRef.value.scrollHeight
}

async function saveCurrentChatAsNote() {
  if (!selectedChat.value) return

  const payload = {
    id: Date.now(),
    class: store.selectedClass?.name || 'General',
    date: new Date().toISOString().slice(0, 10),
    chat: selectedChat.value.title || 'Current chat',
    content: selectedChat.value.title || ''
  }

  console.info('[API trigger] createNote', {
    actor: store.role,
    why: 'User clicked Save as Note on the active chat bubble.',
    sourceChatId: selectedChat.value?.id,
    sourceChatTitle: payload.chat,
    className: payload.class
  })

  await store.createNote(payload)
}

onMounted(async () => {
  const promptFromQuery = route.query?.prompt
  if (typeof promptFromQuery !== 'string' || !promptFromQuery.trim()) return

  prompt.value = promptFromQuery
  if (route.path === '/' && Object.keys(route.query).length) {
    await router.replace({ path: '/', query: {} })
  }
})
</script>
