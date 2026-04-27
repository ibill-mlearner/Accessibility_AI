<template>
  <button class="btn btn-outline-secondary profile-button" type="button" @click="$emit('profile')">Profile</button>
</template>

<script setup>
defineEmits(['profile'])
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/auth/profile-button.css"></style>
