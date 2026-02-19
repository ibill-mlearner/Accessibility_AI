<template>
  <div class="d-flex flex-column gap-2">
    <LoginFormCard v-model:username="username" v-model:password="password" @submit="doLogin" />
    <p v-if="store.authError" class="text-danger mb-0">{{ store.authError }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'
import LoginFormCard from '../components/auth/LoginFormCard.vue'

const router = useRouter()
const route = useRoute()
const store = useAppStore()
const username = ref('')
const password = ref('')

async function doLogin() {
  try {
    await store.login({ email: username.value, password: password.value })
    await store.bootstrap()
    const nextPath = typeof route.query?.next === 'string' ? route.query.next : '/'
    // `next` restores the intended destination, while `prompt` is only forwarded when
    // present so we don't leave an empty query string on normal logins.
    const prompt = typeof route.query?.prompt === 'string' ? route.query.prompt : ''
    await router.push({ path: nextPath, query: prompt ? { prompt } : {} })
  } catch {
    // auth error is set by store.login; remain on /login
  }
}
</script>

<style scoped>
.auth-error {
  margin-top: 0.75rem;
  color: #b42318;
}
</style>
