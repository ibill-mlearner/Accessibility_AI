<template>
  <section class="card bg-light-subtle border-0">
    <div class="card-body d-flex flex-column gap-2">
      <h3 class="h6 text-uppercase text-muted mb-0">Session</h3>
      <p class="mb-0">
        <strong>Session ID:</strong>
        <span class="ms-1">{{ session?.id || 'Unavailable' }}</span>
      </p>
      <div>
        <p class="mb-1"><strong>Allowed actions</strong></p>
        <ul v-if="allowedActions.length" class="mb-0 ps-4">
          <li v-for="action in allowedActions" :key="action">{{ action }}</li>
        </ul>
        <p v-else class="mb-0 text-muted">No actions available.</p>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  session: { type: Object, default: null },
  allowedActions: { type: Array, default: () => [] }
})
</script>
