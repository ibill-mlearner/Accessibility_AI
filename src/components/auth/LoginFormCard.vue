<template>
  <section class="auth-card">
    <input :value="username" @input="$emit('update:username', $event.target.value)" placeholder="Username . . ." />
    <input :value="password" @input="$emit('update:password', $event.target.value)" type="password" placeholder="Password . . ." />
    <button class="icon-btn" @click="$emit('submit')">➤</button>
  </section>
</template>

<script setup>
defineProps({
  username: { type: String, default: '' },
  password: { type: String, default: '' }
})

defineEmits(['submit', 'update:username', 'update:password'])
</script>
