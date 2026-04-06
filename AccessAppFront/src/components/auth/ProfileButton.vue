<template>
  <button class="btn btn-outline-secondary profile-button" type="button" @click="$emit('profile')">Profile</button>
</template>

<script setup>
defineEmits(['profile'])
</script>

<style scoped src="../../styles/components/auth/profile-button.css"></style>
