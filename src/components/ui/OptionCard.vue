<template>
  <article class="card-row">
    <div>
      <p>{{ description }}</p>
      <slot name="selector" />
    </div>
    <slot name="action" />
  </article>
</template>

<script setup>
defineProps({
  description: { type: String, default: '' }
})
</script>
