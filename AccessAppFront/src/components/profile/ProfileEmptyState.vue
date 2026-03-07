<template>
  <section class="card border-warning-subtle">
    <div class="card-body">
      <h3 class="h6 mb-2">Profile details unavailable</h3>
      <p class="mb-3 text-muted">We could not load complete profile data from your active session.</p>
      <button class="btn btn-outline-secondary" type="button" @click="$emit('retry')">Try again</button>
    </div>
  </section>
</template>

<script setup>
defineEmits(['retry'])
</script>
