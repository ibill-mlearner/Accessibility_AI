<template>
  <article class="chat-bubble-card panel" :class="variantClass">
    <slot>{{ text }}</slot>
    <div v-if="showActions" class="button-row">
      <button class="btn" @click="$emit('read-aloud')">Read Aloud</button>
      <button class="btn" @click="$emit('save-note')">Save as Note</button>
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

defineEmits(['read-aloud', 'save-note'])

const variantClass = computed(() => `chat-bubble-card--${props.variant}`)
</script>
