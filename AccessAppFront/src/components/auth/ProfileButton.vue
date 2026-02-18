<template>
  <button class="account-action-btn" type="button" @click="$emit('profile')">Profile</button>
</template>

<script setup>
defineEmits(['profile'])
</script>
