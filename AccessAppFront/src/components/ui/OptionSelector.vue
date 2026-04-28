<template>
  <label class="option-selector">
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

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/ui/option-selector.css"></style>
