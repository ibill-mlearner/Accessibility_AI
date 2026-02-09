<template>
  <section class="cards">
    <HeaderBar />
    <button class="btn" @click="toggleRole">Toggle Role (guest/student)</button>
  </section>
</template>

<script setup>
import HeaderBar from '../../components/HeaderBar.vue'
import { useAppStore } from '../../stores/appStore'

const store = useAppStore()

function toggleRole() {
  store.role = store.role === 'guest' ? 'student' : 'guest'
}
</script>
