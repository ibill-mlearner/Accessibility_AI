<template>
  <section>
    <LoginFormCard v-model:username="username" v-model:password="password" @submit="submitted = true" />
    <p>Username: {{ username }}</p>
    <p>Password length: {{ password.length }}</p>
    <p>Submitted: {{ submitted }}</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import LoginFormCard from '../../components/auth/LoginFormCard.vue'

const username = ref('')
const password = ref('')
const submitted = ref(false)
</script>
