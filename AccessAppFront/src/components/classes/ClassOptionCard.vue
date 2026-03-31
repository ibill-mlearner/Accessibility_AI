<template>
  <article
    :class="['card', 'shadow-sm', checked ? 'border-primary' : '']"
    role="button"
    tabindex="0"
    @click="$emit('select', item.id)"
    @keydown.enter.prevent="$emit('select', item.id)"
    @keydown.space.prevent="$emit('select', item.id)"
  >
    <div class="card-body">
      <h4 class="h6 mb-2">{{ item.name }}</h4>
      <p class="text-muted mb-0">{{ item.description }}</p>
    </div>
  </article>
</template>

<script setup>
defineProps({
  item: { type: Object, required: true },
  checked: { type: Boolean, default: false }
})

defineEmits(['select'])
</script>
