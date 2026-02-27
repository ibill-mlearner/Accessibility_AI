<template>
  <OptionCard :description="featureDescription">
    <template #selector>
      <OptionSelector
        type="checkbox"
        :name="name"
        :label="featureLabel"
        :checked="isActive"
        @change="onToggle"
      />
    </template>
  </OptionCard>
</template>

<script setup>
import { computed } from 'vue';
import OptionCard from '../ui/OptionCard.vue'
import OptionSelector from '../ui/OptionSelector.vue'

const props = deffineProps({
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
  Boolean(props.item?.active ?? props.item?.enabled )
)

function onToggle(event) {
  emit('toggle', event?.target?.checked === true )
}

// defineEmits(['toggle'])
</script>
