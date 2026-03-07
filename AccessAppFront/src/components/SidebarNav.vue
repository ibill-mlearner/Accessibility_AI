<template>
  <aside class="d-flex flex-column gap-3 h-100">
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
        <RouterLink to="/saved-notes" 
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0"
          >
          Saved Notes
        </RouterLink>

        <RouterLink 
          to="/classes" 
          class="btn btn-outline-primary text-start"
          active-class="bg-purple-200 text-dark border-0" >
          My Classes
        </RouterLink>
        
      </div>
    </nav>

    <section v-if="auth.role !== 'guest'" 
      class="card shadow-sm flex-grow overflow-auto">
      <h3>Chats</h3>
      <ul>
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
