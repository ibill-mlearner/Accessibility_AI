<template>
  <section class="card bg-light-subtle border-0 profile-security-card">
    <div class="card-body d-flex flex-wrap gap-2">
      <button class="btn btn-outline-primary" type="button" @click="$emit('retry')">Refresh Session</button>
      <button class="btn btn-outline-danger" type="button" @click="$emit('logout')">Log Out</button>
    </div>
  </section>
</template>

<script setup>
defineEmits(['logout', 'retry'])
</script>

<style scoped src="../../styles/components/profile/profile-security-card.css"></style>
