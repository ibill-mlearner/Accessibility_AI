<template>
  <label>
    <input :type="type" :name="name" :checked="checked" @change="$emit('change', $event)" />
    {{ label }}
  </label>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  checked: { type: Boolean, default: false },
  name: { type: String, default: '' },
  type: { type: String, default: 'radio' }
})

defineEmits(['change'])
</script>
