<template>
  <section class="logout-card">
    <div class="panel">You are logging out . . .</div>
    <div class="panel">Redirect to home new chat - logged out</div>
    <button class="btn" @click="goHome">Complete logout</button>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'

const router = useRouter()
const store = useAppStore()

function goHome() {
  store.logout()
  router.push('/')
}
</script>
