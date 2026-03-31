<template>
  <div style="max-width: 10rem;">
    <label for="profileFontSize" class="form-label small text-uppercase text-muted mb-1">Font size</label>
    <select
      id="profileFontSize"
      :value="modelValue"
      class="form-select form-select-sm"
      @change="onChange"
    >
      <option v-for="size in options" :key="size.value" :value="size.value">
        {{ size.label }}
      </option>
    </select>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

function onChange(event) {
  emit('update:modelValue', event.target.value)
  emit('change')
}
</script>
