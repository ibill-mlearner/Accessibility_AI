<template>
  <button class="btn btn-outline-danger logout-button" type="button" @click="$emit('logout')">Logout</button>
</template>

<script setup>
defineEmits(['logout'])
</script>

<style scoped src="../../styles/components/auth/logout-button.css"></style>
