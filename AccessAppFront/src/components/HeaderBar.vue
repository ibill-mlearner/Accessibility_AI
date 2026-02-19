<template>
  <header class="card shadow-sm" :class="{ 'header-bar--invisible': !store.hasHeaderContext }" :aria-hidden="!store.hasHeaderContext">
    <h1>
      Local Model: {{ store.selectedModel }}
      <span class="header-separator">|</span>
      Class: {{ store.selectedClass?.name || '' }}
    </h1>
  </header>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'

const store = useAppStore()
</script>
