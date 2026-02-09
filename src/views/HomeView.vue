<template>
  <section>
    <ChatBubbleCard text="System's response . . ." variant="system" />
    <ChatBubbleCard text="User's prompt . . ." variant="user" />
    <ComposerBar
      v-model="prompt"
      :selected-model="store.selectedModel"
      :show-login="store.role === 'guest'"
      @login="router.push('/login')"
      @update:selected-model="store.selectedModel = $event"
    />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'
import ChatBubbleCard from '../components/chat/ChatBubbleCard.vue'
import ComposerBar from '../components/chat/ComposerBar.vue'

const router = useRouter()
const store = useAppStore()
const prompt = ref('')
</script>
