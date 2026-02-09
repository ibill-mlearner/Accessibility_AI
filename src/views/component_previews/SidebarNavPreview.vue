<template>
  <section>
    <SidebarNav />
  </section>
</template>

<script setup>
import { onMounted } from 'vue'
import SidebarNav from '../../components/SidebarNav.vue'
import { useAppStore } from '../../stores/appStore'

const store = useAppStore()

onMounted(() => {
  store.chats = [
    { id: 1, title: 'Preview Chat 1' },
    { id: 2, title: 'Preview Chat 2' }
  ]
  store.selectedChatId = 1
})
</script>
