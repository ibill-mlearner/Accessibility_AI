<template>
  <section class="card logout-view">
    <div class="card-body text-center">
      <p class="h4 mb-0">You are logging out . . .</p>
    </div>
  </section>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  authStore.logout()
  router.push('/')
})
</script>

<style scoped src="../styles/views/logout-view.css"></style>
