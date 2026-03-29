<template>
  <aside class="sidebar-nav d-flex flex-column gap-3 h-100">
    <div class="card shadow-sm">
      <div class="card-body d-flex align-items-center gap-2"
        style="font-size: 1.25rem;">
        <img src="/logo.svg" alt="Project logo" 
          style="width:42px; height:42px" />
        <span>AI Project or Logo</span>
      </div>
    </div>

    <nav class="card shadow-sm">
      <div class="card-body d-grid gap-2">
        <button class="btn btn-outline-primary text-start" 
          type="button" 
          @click="handleNewChatClick">
          New Chat
        </button>
        <RouterLink to="/accessibility" 
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0"
          >
          Accessibility Features
        </RouterLink>
        <!-- Intentionally hidden during sprint 4 -->
        <!-- <RouterLink to="/saved-notes" 
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0"
          >
          Saved Notes
        </RouterLink> -->

        <RouterLink 
          to="/classes" 
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0" >
          My Classes
        </RouterLink>
        
      </div>
    </nav>

    <section v-if="auth.role !== 'guest'" 
      class="card shadow-sm flex-grow sidebar-nav__chat-list">
      <h3 class="sidebar-nav__chat-list-title">Chats</h3>
      <ul class="sidebar-nav__chat-list-items">
        <li v-for="chat in chats.chats" 
          :key="chat.id" 
          :class="{ 'bg-purple-200': chat.id === chats.selectedChatId }"
          class="list-group-item p-0">
          <button 
            class="w-100 text-start border-0 bg-transparent px-3 py-2" 
            type="button" 
            @click="selectedChat(chat.id)">
            {{ chat.title }}
          </button>
        </li>
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

<style scoped>
.sidebar-nav {
  min-height: 0;
}

.sidebar-nav__chat-list {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-nav__chat-list-title {
  flex: 0 0 auto;
  margin: 0.75rem 0.75rem 0.25rem;
}

.sidebar-nav__chat-list-items {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  margin: 0;
  padding: 0 0.75rem 0.75rem;
  list-style: none;
}

.sidebar-nav__account-actions {
  flex: 0 0 auto;
}
</style>
