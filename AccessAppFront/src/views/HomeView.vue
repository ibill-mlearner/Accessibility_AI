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
            :is-reading="activeReadAloudMessageId === message.id && speech.isSpeaking"
            :volume="readAloudVolume"
            :selected-voice="selectedReadAloudVoice"
            :voice-options="readAloudVoiceOptions"
            @read-aloud-toggle="handleReadAloudToggle(message)"
            @read-aloud-stop="handleReadAloudStop"
            @read-aloud-volume="handleReadAloudVolume"
            @read-aloud-voice="handleReadAloudVoice"
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
import { useSpeechSynthesis } from '../composables/useSpeechSynthesis'

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
const speech = useSpeechSynthesis()
const isReadAloudSupported = computed(() => speech.isSupported)
const activeReadAloudMessageId = ref(null)
const activeReadAloudText = ref('')
const readAloudVolume = ref(1)
const selectedReadAloudVoice = ref('Samantha')
const readAloudVoiceOptions = [
  { label: 'Samantha', value: 'Samantha' },
  { label: 'Google US English', value: 'Google US English' },
  { label: 'Microsoft Zira - English (United States)', value: 'Microsoft Zira - English (United States)' }
]

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

function handleReadAloudToggle(message) {
  if (!isReadAloudSupported.value || !message?.text?.trim()) return

  const isSameMessage = activeReadAloudMessageId.value === message.id
  if (isSameMessage && speech.isSpeaking.value) {
    speech.stop()
    activeReadAloudMessageId.value = null
    activeReadAloudText.value = ''
    return
  }

  speech.start(message.text, selectedReadAloudVoice.value, readAloudVolume.value)
  activeReadAloudMessageId.value = message.id
  activeReadAloudText.value = message.text
}

function handleReadAloudStop() {
  if (!isReadAloudSupported.value) return
  speech.stop()
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

  if (!speech.isSpeaking.value || !activeReadAloudText.value) return

  speech.start(activeReadAloudText.value, selectedReadAloudVoice.value, readAloudVolume.value)
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
  speech.stop()
})
</script>

<style scoped src="../styles/views/home-view.css"></style>
