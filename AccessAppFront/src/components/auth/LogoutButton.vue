<template>
  <button class="btn btn-outline-danger" type="button" @click="$emit('logout')">Logout</button>
</template>

<script setup>
defineEmits(['logout'])
</script>
