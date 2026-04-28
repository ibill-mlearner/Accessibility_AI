<template>
  <section class="card logout-view">
    <div class="card-body text-center">
      <p class="h4 mb-0">You are logging out . . .</p>
    </div>
  </section>
</template>

<script setup>
// Logout view performs immediate sign-out side effects, then redirects to the home route.
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  // Fire-and-forget logout; auth store handles backend failure tolerance and local cleanup.
  authStore.logout()
  router.push('/')
})
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../styles/views/logout-view.css"></style>
