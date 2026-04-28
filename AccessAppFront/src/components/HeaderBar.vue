<template>
  <header class="card shadow-sm header-bar" :class="{ 'header-bar--invisible': !hasHeaderContext }" :aria-hidden="!hasHeaderContext">
    <h1>
      Class: {{ classStore.selectedClass?.name || '' }}
    </h1>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useClassStore } from '../stores/classStore'

const authStore = useAuthStore()
const classStore = useClassStore()

const hasHeaderContext = computed(() => Boolean(authStore.isAuthenticated && classStore.selectedClass))
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../styles/components/header-bar.css"></style>
