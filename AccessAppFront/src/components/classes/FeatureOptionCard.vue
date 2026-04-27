<template>
  <article class="feature-option-card-wrapper">
    <button
      type="button"
      :class="[
        'card',
        'shadow-sm',
        'feature-option-card',
        'w-100',
        'text-start',
        isActive ? 'feature-option-card--active border-primary' : 'border-transparent'
      ]"
      :aria-pressed="isActive"
      :aria-label="`Toggle ${featureLabel}`"
      @click="onToggle"
    >
      <span class="card-body d-flex flex-column gap-1">
        <span class="h6 mb-1">{{ featureLabel }}</span>
        <span class="text-muted mb-0">{{ featureDescription }}</span>
        <span class="feature-option-card__status" :class="isActive ? 'text-primary' : 'text-muted'">
          {{ isActive ? 'Enabled' : 'Not enabled' }}
        </span>
      </span>
    </button>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true }
})

const emit = defineEmits(['toggle'])

const featureLabel = computed(() =>
  props.item?.title || props.item?.name || 'Accessibility feature'
)

const featureDescription = computed(() =>
  props.item?.details || props.item?.description || ''
)

const isActive = computed(() =>
  Boolean(props.item?.enabled ?? props.item?.active)
)

function onToggle() {
  emit('toggle', !isActive.value)
}
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/classes/feature-option-card.css"></style>
