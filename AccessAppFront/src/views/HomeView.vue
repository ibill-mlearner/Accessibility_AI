<template>
  <section class="home-thread d-flex flex-column gap-2">
    <div ref="messageListRef" class="home-thread__messages overflow-auto" aria-live="polite">
      <div class="d-flex flex-column gap-2">
        <p v-if="interactionError" class="alert alert-danger py-2 mb-0">{{ interactionError }}</p>
        <p v-if="interactionLoading" class="alert alert-info py-2 mb-0">Sending…</p>
        <template v-if="auth.role !== 'guest'">
          <ChatBubbleCard
            v-for="message in conversationMessages"
            :key="message.id"
            :text="message.text"
            :variant="messageVariantMap[message.role] || message.role"
            :show-actions="message.role === 'assistant'"
            :read-aloud-enabled="isReadAloudSupported"
            :is-reading="activeReadAloudMessageId === message.id && isReadAloudPlaying"
            :volume="readAloudVolume"
            @read-aloud-toggle="handleReadAloudToggle(message)"
            @read-aloud-stop="handleReadAloudStop"
            @read-aloud-volume="handleReadAloudVolume"
          />
        </template>
      </div>
    </div>
    <ComposerBar
      v-model="prompt"
      :selected-model="chatStore.selectedModel"
      :model-options="chatStore.modelCatalog"
      :model-loading="chatStore.modelCatalogLoading"
      :show-login="auth.role === 'guest'"
      @login="router.push('/login')"
      @send="sendPrompt"
      @update:selected-model="handleModelSelection"
    />
    <p v-if="chatStore.modelCatalogError" class="alert alert-warning py-2 mb-0" role="status">
      {{ chatStore.modelCatalogError }}
    </p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { useClassStore } from '../stores/classStore'
import { useNoteStore } from '../stores/noteStore'
import { useAutoScroll } from '../composables/useAutoScroll'
import { useChatTimeline } from '../composables/useChatTimeline'
import { useSendPrompt } from '../composables/useSendPrompt'

import ChatBubbleCard from '../components/chat/ChatBubbleCard.vue'
import ComposerBar from '../components/chat/ComposerBar.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const chatStore = useChatStore()
const classStore = useClassStore()
const noteStore = useNoteStore()
const { messageListRef, scrollToLatestTurn } = useAutoScroll()
const { timelineMessages, interactionError, hydrateTimelineForChat } = useChatTimeline(chatStore)
const { prompt, interactionLoading, sendPrompt } = useSendPrompt({ auth, router, chatStore, classStore, timelineMessages, scrollToLatestTurn, interactionError })
const isReadAloudSupported = typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function'

const activeReadAloudMessageId = ref(null)
const isReadAloudPlaying = ref(false)
const readAloudVolume = ref(1)
const currentUtterance = ref(null)

const messageVariantMap = {
  assistant: 'system',
  system: 'system',
  user: 'user'
}
const selectedChat = computed(() => chatStore.chats.find((chat) => chat.id === chatStore.selectedChatId) || null)
const conversationMessages = computed(() =>
  timelineMessages.value.length ? timelineMessages.value.map((message) =>
    ({ ...message, text: message.unsaved ? `${message.text} (unsaved)` : message.text })) : [{
      id: selectedChat.value?.id ?? 'assistant-preview',
      role: 'assistant',
      text: selectedChat.value?.title || "System's response . . ."
    },
    {
      id: 'user-preview', role: 'user',
      text: "User's prompt . . ."
    }])

async function handleModelSelection(modelValue) {
  await chatStore.updateModelSelection(modelValue)
}

function clearReadAloudState() {
  activeReadAloudMessageId.value = null
  isReadAloudPlaying.value = false
  currentUtterance.value = null
}

function handleReadAloudToggle(message) {
  if (!isReadAloudSupported || !message?.text?.trim()) return

  const isSameMessage = activeReadAloudMessageId.value === message.id
  if (isSameMessage && window.speechSynthesis.speaking) {
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume()
      isReadAloudPlaying.value = true
    } else {
      window.speechSynthesis.pause()
      isReadAloudPlaying.value = false
    }
    return
  }

  window.speechSynthesis.cancel()

  const utterance = new window.SpeechSynthesisUtterance(message.text)
  utterance.lang = 'en-US'
  utterance.volume = readAloudVolume.value

  utterance.onstart = () => {
    activeReadAloudMessageId.value = message.id
    isReadAloudPlaying.value = true
  }

  utterance.onend = () => {
    clearReadAloudState()
  }

  utterance.onerror = () => {
    clearReadAloudState()
  }

  currentUtterance.value = utterance
  window.speechSynthesis.speak(utterance)
}

function handleReadAloudStop() {
  if (!isReadAloudSupported) return
  window.speechSynthesis.cancel()
  clearReadAloudState()
}

function handleReadAloudVolume(nextVolume) {
  const normalizedVolume = Number(nextVolume)
  if (Number.isNaN(normalizedVolume)) return

  readAloudVolume.value = Math.min(1, Math.max(0, normalizedVolume))

  if (currentUtterance.value) {
    currentUtterance.value.volume = readAloudVolume.value
  }
}

async function saveCurrentChatAsNote() {
  if (!selectedChat.value) return
  await noteStore.createNote({
    id: Date.now(),
    class: classStore.selectedClass?.name || 'General',
    date: new Date().toISOString().slice(0, 10),
    chat: selectedChat.value.title || 'Current chat',
    content: selectedChat.value.title || ''
  })
}

watch(() => chatStore.newChatRequestId, () => {
  timelineMessages.value = []
  interactionError.value = ''
  interactionLoading.value = false
  handleReadAloudStop()
})

watch(() => chatStore.selectedChatId, async (chatId) => {
  interactionError.value = ''
  handleReadAloudStop()
  await hydrateTimelineForChat(chatId)
},
{
  immediate: true
}
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

onBeforeUnmount(() => {
  if (!isReadAloudSupported) return
  window.speechSynthesis.cancel()
})
</script>

<style scoped src="../styles/views/home-view.css"></style>
