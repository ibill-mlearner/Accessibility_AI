<template>
  <article class="chat-bubble-card panel" :class="variantClass">
    <slot>{{ text }}</slot>
    <div v-if="showActions" class="button-row">
      <button class="btn">Read Aloud</button>
      <button class="btn">Save as Note</button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  variant: { type: String, default: 'system' },
  showActions: { type: Boolean, default: false }
})

const variantClass = computed(() => `chat-bubble-card--${props.variant}`)
</script>
