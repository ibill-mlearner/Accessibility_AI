<template>
  <section class="card">
    <div class="card-body text-center">
      <p class="h4 mb-0">You are logging out . . .</p>
    </div>
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
