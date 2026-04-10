<template>
  <div class="chat-bubble-card__actions">
    <span class="chat-bubble-card__actions-label">Read aloud</span>
    <div class="chat-bubble-card__controls" :aria-disabled="!readAloudEnabled">
      <button
        class="btn btn-secondary btn-sm chat-bubble-card__control-btn"
        :disabled="!readAloudEnabled"
        :aria-disabled="!readAloudEnabled"
        @click="$emit('toggle')"
      >
        {{ isReading ? 'Pause' : 'Play' }}
      </button>
      <button
        class="btn btn-outline-secondary btn-sm chat-bubble-card__control-btn"
        :disabled="!readAloudEnabled"
        :aria-disabled="!readAloudEnabled"
        @click="$emit('stop')"
      >
        Stop
      </button>
      <label class="chat-bubble-card__volume-wrap">
        <span class="chat-bubble-card__volume-label">Volume</span>
        <input
          class="form-range chat-bubble-card__volume"
          type="range"
          min="0"
          max="1"
          step="0.1"
          :value="volume"
          :disabled="!readAloudEnabled"
          @input="$emit('volume', Number($event.target.value))"
        >
      </label>
    </div>
  </div>
</template>

<script setup>
defineProps({
  readAloudEnabled: { type: Boolean, default: true },
  isReading: { type: Boolean, default: false },
  volume: { type: Number, default: 1 }
})

defineEmits(['toggle', 'stop', 'volume'])
</script>

<style scoped src="../../styles/components/chat/chat-bubble-card.css"></style>
