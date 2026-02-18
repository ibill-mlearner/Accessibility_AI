<template>
  <section class="logout-card">
    <div class="panel">You are logging out . . .</div>
  </section>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'

const router = useRouter()
const store = useAppStore()

onMounted(() => {
  store.logout()
  router.push('/')
})
</script>
