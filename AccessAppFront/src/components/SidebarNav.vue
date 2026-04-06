<template>
  <aside class="sidebar-nav d-flex flex-column gap-3 h-100">
    <div class="card shadow-sm">
      <div class="card-body d-flex align-items-center gap-2 sidebar-nav__brand">
        <img src="/logo.svg" alt="Project logo" class="sidebar-nav__brand-logo" />
        <span>AI Project or Logo</span>
      </div>
    </div>

    <nav class="card shadow-sm">
      <div class="card-body d-grid gap-2">
        <button
          class="btn btn-outline-primary text-start"
          type="button"
          @click="handleNewChatClick"
        >
          New Chat
        </button>
        <RouterLink
          to="/accessibility"
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0"
        >
          Accessibility Features
        </RouterLink>

        <RouterLink
          to="/classes"
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0"
        >
          My Classes
        </RouterLink>
      </div>
    </nav>

    <section
      v-if="auth.role !== 'guest'"
      class="card shadow-sm flex-grow sidebar-nav__chat-list"
    >
      <h3 class="sidebar-nav__chat-list-title">Chats</h3>
      <ul class="sidebar-nav__chat-list-items">
        <ChatListItem
          v-for="chat in chats.chats"
          :key="chat.id"
          :chat="chat"
          :is-active="chat.id === chats.selectedChatId"
          @select="selectedChat"
        />
      </ul>
    </section>

    <div class="sidebar-nav__account-actions mt-auto">
      <AccountActionsCard
        :is-logged-in="isLoggedIn"
        @profile="router.push('/profile')"
        @logout="handleLogout"
      />
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AccountActionsCard from './auth/AccountActionsCard.vue'
import ChatListItem from './chat/ChatListItem.vue'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'

const router = useRouter()
const auth = useAuthStore()
const chats = useChatStore()
const isLoggedIn = computed(() => auth.isAuthenticated && auth.role !== 'guest')

async function handleLogout() {
  await auth.logout()
  router.push('/')
}

function handleNewChatClick() {
  chats.prepareNewChat()
  router.push('/')
}

function selectedChat(id) {
  chats.selectedChatId = id
  router.push('/')
}
</script>

<style scoped src="../styles/components/sidebar-nav.css"></style>
