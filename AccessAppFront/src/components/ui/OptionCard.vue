<template>
  <article class="card-row option-card">
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

<style scoped src="../../styles/components/ui/option-card.css"></style>
