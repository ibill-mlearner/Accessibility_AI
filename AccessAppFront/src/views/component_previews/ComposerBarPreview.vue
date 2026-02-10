<template>
  <section class="cards">
    <ComposerBar v-model="prompt" :selected-model="selectedModel" :show-login="true" @login="loggedIn = true" @send="sent = true" @update:selected-model="selectedModel = $event" />
    <p>Prompt: {{ prompt }}</p>
    <p>Selected Model: {{ selectedModel }}</p>
    <p>Login clicked: {{ loggedIn }}</p>
    <p>Send clicked: {{ sent }}</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import ComposerBar from '../../components/chat/ComposerBar.vue'

const prompt = ref('')
const selectedModel = ref('')
const loggedIn = ref(false)
const sent = ref(false)
</script>
