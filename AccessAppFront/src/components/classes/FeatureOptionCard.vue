<template>
  <OptionCard :description="item.description">
    <template #selector>
      <OptionSelector :name="name" :label="item.title" :checked="item.enabled" @change="$emit('toggle', $event.target.checked)" />
    </template>
  </OptionCard>
</template>

<script setup>
import OptionCard from '../ui/OptionCard.vue'
import OptionSelector from '../ui/OptionSelector.vue'

defineProps({
  item: { type: Object, required: true },
  name: { type: String, default: 'feature' }
})

defineEmits(['toggle'])
</script>
