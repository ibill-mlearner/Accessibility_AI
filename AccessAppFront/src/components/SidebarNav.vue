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

    <section v-if="store.role !== 'guest'" class="chat-list chat-list--sessions">
      <h3>Chats</h3>
      <ul>
        <li v-for="chat in store.chats" :key="chat.id" :class="{ active: chat.id === store.selectedChatId }">
          <button class="chat-item" type="button" @click="store.selectedChatId = chat.id">
            {{ chat.title }}
          </button>
        </li>
      </ul>
    </section>

    <AccountActionsCard
      :is-logged-in="isLoggedIn"
      @profile="router.push('/profile')"
      @logout="handleLogout"
    />
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AccountActionsCard from './auth/AccountActionsCard.vue'
import { useAppStore } from '../stores/appStore'

const router = useRouter()
const store = useAppStore()
const isLoggedIn = computed(() => store.isAuthenticated && store.role !== 'guest')

function handleLogout() {
  store.logout()
  router.push('/')
}
</script>
