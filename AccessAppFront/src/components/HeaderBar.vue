<template>
  <header class="header-bar">
    <h1>{{ store.topHeader }}</h1>
    <p>Reserved spacing for headers</p>
  </header>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
const store = useAppStore()
</script>
