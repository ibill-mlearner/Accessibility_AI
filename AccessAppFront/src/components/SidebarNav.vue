<template>
  <aside class="sidebar">
    <div class="logo-card">
      <img src="/logo.svg" alt="Project logo" />
      <span>AI Project or Logo</span>
    </div>

    <nav class="menu-card">
      <RouterLink to="/" class="menu-item">New Chat</RouterLink>
      <RouterLink to="/accessibility" class="menu-item">Accessibility Features</RouterLink>
      <RouterLink to="/saved-notes" class="menu-item">Saved Notes</RouterLink>
      <RouterLink :to="`/classes/${store.role === 'instructor' ? 'instructor' : 'student'}`" class="menu-item">
        My Classes
      </RouterLink>
    </nav>

    <section v-if="store.role !== 'guest'" class="chat-list">
      <h3>Chats</h3>
      <ul>
        <li v-for="chat in store.chats" :key="chat.id" :class="{ active: chat.id === store.selectedChatId }">
          <button class="chat-item" type="button" @click="store.selectedChatId = chat.id">
            {{ chat.title }}
          </button>
        </li>
      </ul>
    </section>
  </aside>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'

const store = useAppStore()
</script>
