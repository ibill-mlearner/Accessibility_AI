<template>
  <header class="card shadow-sm header-bar" :class="{ 'header-bar--invisible': !hasHeaderContext }" :aria-hidden="!hasHeaderContext">
    <h1>
      Local Model: {{ selectedModelLabel }}
      <span class="header-separator">|</span>
      Class: {{ classStore.selectedClass?.name || '' }}
    </h1>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { useClassStore } from '../stores/classStore'

const authStore = useAuthStore()
const chatStore = useChatStore()
const classStore = useClassStore()

const selectedModelLabel = computed(() => {
  const selectedValue = String(chatStore.selectedModel || '').trim()
  if (!selectedValue) return 'No model selected'

  const selectedOption = chatStore.modelCatalog.find((option) => option.value === selectedValue)
  return selectedOption?.label || selectedValue
})

const hasHeaderContext = computed(() => Boolean(authStore.isAuthenticated && classStore.selectedClass))
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../styles/components/header-bar.css"></style>
