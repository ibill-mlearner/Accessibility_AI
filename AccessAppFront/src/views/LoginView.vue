<template>
  <div>
    <LoginFormCard v-model:username="username" v-model:password="password" @submit="doLogin" />
    <p v-if="store.authError" class="auth-error">{{ store.authError }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'
import LoginFormCard from '../components/auth/LoginFormCard.vue'

const router = useRouter()
const store = useAppStore()
const username = ref('')
const password = ref('')

async function doLogin() {
  try {
    await store.login({ email: username.value, password: password.value })
    await router.push('/')
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
