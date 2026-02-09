<template>
  <div v-if="isComponentPreviewRoute" class="preview-only-layout">
    <router-view />
  </div>
  <div v-else class="layout">
    <SidebarNav />
    <main class="content">
      <HeaderBar />
      <p v-if="store.error" class="error-banner">{{ store.error }}</p>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from './stores/appStore'
import SidebarNav from './components/SidebarNav.vue'
import HeaderBar from './components/HeaderBar.vue'

const route = useRoute()
const store = useAppStore()

const isComponentPreviewRoute = computed(() => route.path.startsWith('/component-previews/'))

onMounted(() => {
  store.bootstrap()
})
</script>
