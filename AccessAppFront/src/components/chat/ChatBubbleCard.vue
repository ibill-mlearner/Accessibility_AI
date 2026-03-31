<template>
  <article class="card shadow-sm" :class="variantClass" style="max-width: min(80%, 680px)">
    <div class="card shadow-sm border border-3">
      <slot>{{ text }}</slot>
      <div v-if="showActions" 
        class="d-flex justify-content-between mt-1 gap-1">
        <button
          class="btn btn-secondary px-2 py-1 btn-sm"
          :disabled="!readAloudEnabled"
          :aria-disabled="!readAloudEnabled"
          @click="$emit('read-aloud')"
        >
          {{ readAloudEnabled ? 'Read Aloud' : 'Read Aloud Unavailable' }}
        </button>
        <!-- Intentionally hidden during sprint 4 -->
        <!-- <button class="btn btn-secondary px-2 py-1 btn-sm" @click="$emit('save-note')">Save as Note</button> -->
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  variant: { type: String, default: 'system' },
  showActions: { type: Boolean, default: false },
  readAloudEnabled: { type: Boolean, default: true }
})

defineEmits(['read-aloud'/*, 'save-note'*/])
const variantClass = computed(() => {
  if (props.variant === 'user') return 'ms-auto border-primary'
  return 'me-auto border-secondary'
})

</script>
