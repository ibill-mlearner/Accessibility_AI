<template>
  <button class="btn btn-outline-secondary" type="button" @click="$emit('profile')">Profile</button>
</template>

<script setup>
defineEmits(['profile'])
</script>
