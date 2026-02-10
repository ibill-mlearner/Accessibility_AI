<template>
  <LoginFormCard v-model:username="username" v-model:password="password" @submit="doLogin" />
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
    await store.login(username.value, password.value)
    router.push('/')
  } catch (error) {
    router.push('/error')
  }
}
</script>
