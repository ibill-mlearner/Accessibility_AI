<template>
  <article :class="['card', 'shadow-sm', isActive ? 'border-primary' : '']">
    <div class="card-body d-flex flex-column flex-md-row justify-content-between gap-3 align-items-md-start">
      <div>
        <h4 class="h6 mb-1">{{ featureLabel }}</h4>
        <p class="text-muted mb-0">{{ featureDescription }}</p>
      </div>
      <div class="pt-1">
        <OptionSelector
          type="checkbox"
          :name="name"
          :label="'Enabled'"
          :checked="isActive"
          @change="onToggle"
        />
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue';
import OptionSelector from '../ui/OptionSelector.vue'

const props = defineProps({
  item: { type: Object, required: true},
  name: { type: String, default: 'feature' }
})

const emit = defineEmits(['toggle'])

const featureLabel = computed( () =>
  props.item?.title || props.item?.name || 'Accessibility feature'
) 

const featureDescription = computed( () =>
  props.item?.details || props.item?.description || ''
)

const isActive = computed( () =>
  Boolean(props.item?.enabled ?? props.item?.active )
)

function onToggle(event) {
  emit('toggle', event?.target?.checked === true )
}

// defineEmits(['toggle'])
</script>
