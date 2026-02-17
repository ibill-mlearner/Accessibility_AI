<template>
  <button class="account-action-btn" type="button" @click="$emit('logout')">Logout</button>
</template>

<script setup>
defineEmits(['logout'])
</script>
