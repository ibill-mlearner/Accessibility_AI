<template>
  <article class="card shadow-sm chat-bubble-card" :class="variantClass">
    <div class="card shadow-sm border border-3">
      <slot>
        <div class="chat-bubble-card__content">{{ text }}</div>
      </slot>
      <ReadAloudControls
        v-if="showActions"
        :read-aloud-enabled="readAloudEnabled"
        :is-reading="isReading"
        :volume="volume"
        :selected-voice="selectedVoice"
        :voice-options="voiceOptions"
        @toggle="$emit('read-aloud-toggle')"
        @stop="$emit('read-aloud-stop')"
        @volume="$emit('read-aloud-volume', $event)"
        @voice="$emit('read-aloud-voice', $event)"
      />
      <!-- Intentionally hidden during sprint 4 -->
      <!-- <button class="btn btn-secondary px-2 py-1 btn-sm" @click="$emit('save-note')">Save as Note</button> -->
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import ReadAloudControls from './ReadAloudControls.vue'

// Intentionally presentation-only: this component renders UI and bubbles user intent up via emits.
const props = defineProps({
  text: { type: String, default: '' },
  variant: { type: String, default: 'system' },
  showActions: { type: Boolean, default: false },
  readAloudEnabled: { type: Boolean, default: true },
  isReading: { type: Boolean, default: false },
  volume: { type: Number, default: 1 },
  selectedVoice: { type: String, default: 'Samantha' },
  voiceOptions: {
    type: Array,
    default: () => ([])
  }
})

defineEmits(['read-aloud-toggle', 'read-aloud-stop', 'read-aloud-volume', 'read-aloud-voice'/*, 'save-note'*/])
const variantClass = computed(() => {
  if (props.variant === 'user') return 'ms-auto border-primary'
  return 'me-auto border-secondary'
})
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/chat/chat-bubble-card.css"></style>
