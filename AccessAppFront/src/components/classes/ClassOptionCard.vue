<template>
  <OptionCard :description="item.description">
    <template #selector>
      <OptionSelector :name="name" :label="item.name" :checked="checked" @change="$emit('select', item.id)" />
    </template>
    <template #action>
      <button class="btn">{{ actionLabel }}</button>
    </template>
  </OptionCard>
</template>

<script setup>
import OptionCard from '../ui/OptionCard.vue'
import OptionSelector from '../ui/OptionSelector.vue'

defineProps({
  item: { type: Object, required: true },
  checked: { type: Boolean, default: false },
  actionLabel: { type: String, default: '' },
  name: { type: String, default: 'class' }
})

defineEmits(['select'])
</script>
