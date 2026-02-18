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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
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
const timelineLoadRequestId = ref(0)


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

function hasPromptTemplateLeakage(text) {
  const blockedMarkers = [
    'you are a json api assistant',
    'user prompt:',
    'context json:',
    'required response schema:',
    'user response:'
  ]

  const normalized = String(text || '').toLowerCase()
  return blockedMarkers.some((marker) => normalized.includes(marker))
}

function readAssistantText(aiPayload) {
  const candidateValues = [
    aiPayload?.assistant_text,
    aiPayload?.result,
    aiPayload?.answer,
    aiPayload?.response?.summary,
    aiPayload?.response,
    aiPayload?.summary,
    typeof aiPayload === 'string' ? aiPayload : ''
  ]

  for (const candidateValue of candidateValues) {
    if (typeof candidateValue !== 'string') continue
    const cleaned = candidateValue.trim()
    if (!cleaned) continue
    if (hasPromptTemplateLeakage(cleaned)) return ''
    return cleaned
  }

  return ''
}


function buildFirstChatTitle(cleanPrompt, fallbackIndex) {
  // Normalize prompt whitespace and keep only meaningful words.
  const titleTokens = cleanPrompt.trim().split(/\s+/).filter(Boolean).slice(0, 3)
  // Use an indexed fallback when no words are present after trimming.
  return titleTokens.join(' ') || `New Chat ${fallbackIndex}`
}

function parseTimelineTimestamp(value, fallbackIndex = 0) {
  const parsed = Date.parse(value || '')
  if (Number.isNaN(parsed)) return Number.MAX_SAFE_INTEGER - (100000 - fallbackIndex)
  return parsed
}

function buildTimelineFromInteractions(interactions = []) {
  const turns = []

  interactions.forEach((interaction, index) => {
    const interactionId = interaction?.id ?? `unknown-${index}`
    const createdAt = interaction?.created_at || null

    const promptText = String(interaction?.prompt || '').trim()
    if (promptText) {
      turns.push({
        id: `interaction-${interactionId}-user`,
        role: 'user',
        text: promptText,
        createdAt,
        order: index * 2
      })
    }

    const assistantText = String(interaction?.response_text || '').trim()
    if (assistantText) {
      turns.push({
        id: `interaction-${interactionId}-assistant`,
        role: 'assistant',
        text: assistantText,
        createdAt,
        order: index * 2 + 1
      })
    }
  })

  return turns
}

function buildTimelineFromMessages(messages = []) {
  return messages.map((message, index) => ({
    id: message.id,
    role: index % 2 === 0 ? 'user' : 'assistant',
    text: String(message?.message_text || '').trim(),
    createdAt: null,
    order: index
  }))
}

async function hydrateTimelineForChat(chatId) {
  if (!chatId) {
    timelineMessages.value = []
    return
  }

  const requestId = timelineLoadRequestId.value + 1
  timelineLoadRequestId.value = requestId

  try {
    const [interactions, messages] = await Promise.all([
      store.fetchChatInteractions(chatId),
      store.fetchChatMessages(chatId)
    ])

    if (timelineLoadRequestId.value !== requestId) return

    const sourceMessages = interactions.length
      ? buildTimelineFromInteractions(interactions)
      : buildTimelineFromMessages(messages)

    timelineMessages.value = sourceMessages
      .filter((message) => Boolean(message.text))
      .sort((a, b) => {
        const aTime = parseTimelineTimestamp(a.createdAt, a.order)
        const bTime = parseTimelineTimestamp(b.createdAt, b.order)
        if (aTime !== bTime) return aTime - bTime
        return (a.order ?? 0) - (b.order ?? 0)
      })
      .map(({ id, role, text }) => ({ id, role, text }))
  } catch {
    if (timelineLoadRequestId.value !== requestId) return
    interactionError.value = 'Unable to load chat history right now.'
  }
}


async function sendPrompt() {
  if (interactionLoading.value) return

  const cleanPrompt = prompt.value.trim()
  if (!cleanPrompt) return

  // TODO(security-plan): Consider an optional preflight adversarial prompt-injection check
  // before creating/storing messages. Proposed flow: (1) send `cleanPrompt` to a
  // lightweight classifier policy prompt (same model or dedicated guardrail model),
  // (2) require a structured verdict like {allow, risk_level, reason}, and
  // (3) block or require confirmation on medium/high risk while logging the verdict
  // for audit analysis. This is a planning note and may be toggled via feature flag.
  if (store.role === 'guest') {
    interactionError.value = 'Please log in to send a prompt.'
    await router.push({ path: '/login', query: { next: '/', prompt: cleanPrompt } })
    return
  }

  const draftPrompt = prompt.value
  const classIdForChat = store.selectedClassId || store.classes[0]?.id
  if (!classIdForChat) {
    interactionError.value = 'No class is available for this account yet.'
    return
  }

  interactionLoading.value = true
  interactionError.value = ''

  const messageIntent = 'summarization'

  try {
    // Generate title only for first-chat initialization; existing titles are not overwritten here.
    const firstChatTitle = buildFirstChatTitle(cleanPrompt, store.chats.length + 1)

    // Pass generated title through ensureActiveChat creation path.
    const ensuredChat = await withSingleRetry(() =>
      store.ensureActiveChat({
        // Use helper-derived token title in place of character slicing.
        title: firstChatTitle,
        started_at: new Date().toISOString(),
        model: store.selectedModel || 'General',
        class_id: classIdForChat,
        user_id: store.currentUser?.id
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
      aiResponse = await store.requestAiInteraction({
        prompt: cleanPrompt,
        chat_id: ensuredChat.id,
        context: {
          chat_id: ensuredChat.id,
          class_id: classIdForChat,
          messages: [{ role: 'user', content: cleanPrompt }]
        }
      })
    } catch (error) {
      console.info('[AI interaction error payload]', error?.response?.data)
      const status = error?.response?.status
      interactionError.value =
        status === 400
          ? 'Prompt was rejected. Please edit and retry.'
          : 'AI is temporarily unavailable. Please retry.'
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


watch(
  () => store.newChatRequestId,
  () => {
    timelineMessages.value = []
    interactionError.value = ''
    interactionLoading.value = false
  }
)

watch(
  () => store.selectedChatId,
  async (chatId) => {
    interactionError.value = ''
    await hydrateTimelineForChat(chatId)
  },
  { immediate: true }
)

onMounted(async () => {
  const promptFromQuery = route.query?.prompt
  if (typeof promptFromQuery === 'string' && promptFromQuery.trim()) {
    prompt.value = promptFromQuery
    if (route.path === '/' && Object.keys(route.query).length) {
      await router.replace({ path: '/', query: {} })
    }
  }
})
</script>
