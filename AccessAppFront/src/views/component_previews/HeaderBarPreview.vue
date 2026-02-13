<template>
  <section class="cards">
    <HeaderBar />
    <div class="card-row">
      <button class="btn" @click="toggleModel">Toggle Local Model</button>
      <button class="btn" @click="toggleChat">Toggle Active Chat</button>
      <button class="btn" @click="toggleClass">Toggle Active Class</button>
    </div>
    <p>Local Model: {{ store.selectedModel || '(none)' }}</p>
    <p>Selected Chat: {{ store.selectedChatId || '(none)' }}</p>
    <p>Selected Class: {{ store.selectedClass?.name || '(none)' }}</p>
  </section>
</template>

<script setup>
import HeaderBar from '../../components/HeaderBar.vue'
import { useAppStore } from '../../stores/appStore'

const store = useAppStore()
store.role = 'student'
store.chats = [{ id: 1, title: 'Preview Chat' }]
store.classes = [{ id: 1, role: 'student', name: 'Biology 103' }]

function toggleModel() {
  store.selectedModel = store.selectedModel ? '' : 'Llama 3.1 8B (local)'
}

function toggleChat() {
  store.selectedChatId = store.selectedChatId ? null : 1
}

function toggleClass() {
  store.selectedClassId = store.selectedClassId ? null : 1
}
</script>
