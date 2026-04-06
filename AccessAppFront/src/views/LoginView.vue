<template>
  <div class="login-view d-flex flex-column gap-2">
    <LoginFormCard v-model:email="email" v-model:password="password" @submit="doLogin" />
    <p class="mb-0 text-muted small">
      Seeded users must sign in with their full email address.
    </p>
    <p v-if="auth.authError" class="text-danger mb-0">{{ auth.authError }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useAppBootstrapStore } from '../stores/appBootstrapStore'
import { useChatStore } from '../stores/chatStore'
import LoginFormCard from '../components/auth/LoginFormCard.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const bootstrap = useAppBootstrapStore()
const chatStore = useChatStore()
const email = ref('')
const password = ref('')

async function doLogin() {
  try {
    await auth.login({ email: email.value, password: password.value })
    await bootstrap.bootstrap()
    const nextPath = typeof route.query?.next === 'string' ? route.query.next : '/'
    const prompt = typeof route.query?.prompt === 'string' ? route.query.prompt : ''
    if (nextPath === '/') {
      chatStore.prepareNewChat()
    }
    await router.push({ path: nextPath, query: prompt ? { prompt } : {} })
  } catch {
    // auth error is set by store.login; remain on /login
  }
}
</script>

<style scoped src="../styles/views/login-view.css"></style>
