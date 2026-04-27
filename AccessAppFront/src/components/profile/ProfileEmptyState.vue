<template>
  <section class="card border-warning-subtle profile-empty-state">
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

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/profile/profile-empty-state.css"></style>
