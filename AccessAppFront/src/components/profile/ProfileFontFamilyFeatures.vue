<template>
  <div class="profile-font-family-features">
    <p class="form-label small text-uppercase text-muted mb-2">Font family</p>
    <div class="d-flex flex-wrap gap-2">
      <label
        v-for="option in options"
        :key="option.value"
        :class="[
          'btn',
          'btn-sm',
          'rounded-pill',
          modelValue === option.value ? 'btn-primary' : 'btn-outline-secondary'
        ]"
      >
        <input
          class="visually-hidden"
          type="radio"
          name="profileFontFamily"
          :value="option.value"
          :checked="modelValue === option.value"
          @change="onChange(option.value)"
        />
        <span :class="fontFamilyClass(option.value)">{{ option.label }}</span>
      </label>
    </div>
    <p class="small text-muted mt-2 mb-0">
      Placeholder selector options for future mapped accommodation records.
    </p>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: 'default'
  },
  options: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

function onChange(value) {
  emit('update:modelValue', value)
  emit('change', value)
}
function fontFamilyClass(value) {
  return `profile-font-family-features__sample profile-font-family-features__sample--${value || "default"}`
}
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/profile/profile-font-family-features.css"></style>
