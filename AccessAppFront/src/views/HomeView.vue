<template>
  <section class="chat-thread">
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
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'
import ChatBubbleCard from '../components/chat/ChatBubbleCard.vue'
import ComposerBar from '../components/chat/ComposerBar.vue'

const router = useRouter()
const store = useAppStore()
// Development-only API trigger logging for integration debugging.
// TODO(v1.0): Remove console logging before release.
const prompt = ref('')

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

const conversationMessages = computed(() => [
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
])

async function sendPrompt() {
  const cleanPrompt = prompt.value.trim()
  if (!cleanPrompt || store.role === 'guest') return

  const payload = {
    id: Date.now(),
    title: cleanPrompt.slice(0, 60),
    start: new Date().toISOString(),
    model: store.selectedModel || 'General',
    class: store.selectedClass?.name || '',
    user: store.role
  }

  console.info('[API trigger] createChat', {
    actor: store.role,
    why: 'User submitted a new prompt from the home composer.',
    chatTitle: payload.title,
    className: payload.class,
    model: payload.model
  })

  await store.createChat(payload)
  prompt.value = ''
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
</script>
