<template>
  <section>
    <div class="panel system">System's response . . .</div>
    <div class="panel user">User's prompt . . .</div>
    <div class="composer-row">
      <button v-if="store.role === 'guest'" class="btn" @click="router.push('/login')">Login</button>
      <button class="icon-btn">➤</button>
      <input placeholder="Type here . . ." />
      <select>
        <option>Model selection . . .</option>
        <option>General</option>
        <option>Lecture Assistant</option>
      </select>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/appStore'

const router = useRouter()
const store = useAppStore()
</script>
