<template>
  <article class="class-option-card-wrapper">
    <button
      type="button"
      :class="['card', 'shadow-sm', 'w-100', 'text-start', checked ? 'border-primary' : 'border-transparent']"
      :aria-pressed="checked"
      :aria-label="`Select ${item.name}`"
      @click="$emit('select', item.id)"
    >
      <span class="card-body d-block">
        <span class="h6 d-block mb-2">{{ item.name }}</span>
        <span class="text-muted mb-0 d-block">{{ item.description }}</span>
      </span>
    </button>
  </article>
</template>

<script setup>
defineProps({
  item: { type: Object, required: true },
  checked: { type: Boolean, default: false }
})

defineEmits(['select'])
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/classes/class-option-card.css"></style>
