<template>
  <button class="btn btn-outline-danger logout-button" type="button" @click="$emit('logout')">Logout</button>
</template>

<script setup>
defineEmits(['logout'])
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/auth/logout-button.css"></style>
