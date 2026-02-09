<template>
  <div class="layout">
    <SidebarNav />
    <main class="content">
      <HeaderBar />
      <p v-if="store.error" class="error-banner">{{ store.error }}</p>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/appStore'
import SidebarNav from './components/SidebarNav.vue'
import HeaderBar from './components/HeaderBar.vue'

const store = useAppStore()
onMounted(() => {
  store.bootstrap()
})
</script>
