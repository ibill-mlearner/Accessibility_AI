<template>
  <section class="auth-card">
    <input placeholder="Username . . ." />
    <input type="password" placeholder="Password . . ." />
    <button class="icon-btn" @click="doLogin">➤</button>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'

const router = useRouter()
const store = useAppStore()

function doLogin() {
  store.login()
  router.push('/')
}
</script>
