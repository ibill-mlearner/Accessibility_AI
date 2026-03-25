<template>
  <section class="home-thread d-flex flex-column gap-2">
    <div ref="messageListRef" class="home-thread__messages overflow-auto" aria-live="polite">
      <div class="d-flex flex-column gap-2">
        <p v-if="interactionError" class="alert alert-danger py-2 mb-0">{{ interactionError }}</p>
        <p v-if="interactionLoading" class="alert alert-info py-2 mb-0">Sending…</p>
        <template v-if="auth.role !== 'guest'">
          <!-- save as note button @save-note removed during sprint 4 -->
          <ChatBubbleCard
            v-for="message in conversationMessages"
            :key="message.id"
            :text="message.text"
            :variant="messageVariantMap[message.role] || message.role"
            :show-actions="message.role === 'assistant'"
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
import { computed, onMounted, watch } from 'vue'
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
      text: prompt.value || "User's prompt . . ." 
    }])

async function handleModelSelection(modelValue) {
  await chatStore.updateModelSelection(modelValue)
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
  }
)

watch(() => chatStore.selectedChatId, async (chatId) => {
    interactionError.value = ''
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

</script>

<style scoped>
.home-thread {
  flex: 1 1 auto;
  min-height: 0;
}

.home-thread__messages {
  flex: 1 1 auto;
  min-height: 0;
  padding-right: 0.25rem;
}
</style>
