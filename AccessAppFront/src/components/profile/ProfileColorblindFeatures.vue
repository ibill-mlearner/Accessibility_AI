<template>
  <div class="profile-colorblind-features">
    <p class="form-label small text-uppercase text-muted mb-2">Colorblind features</p>
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
          name="profileColorblindType"
          :value="option.value"
          :checked="modelValue === option.value"
          @change="$emit('update:modelValue', option.value)"
        />
        {{ option.label }}
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
    default: 'none'
  },
  options: {
    type: Array,
    default: () => []
  }
})

defineEmits(['update:modelValue'])
</script>

<style scoped src="../../styles/components/profile/profile-colorblind-features.css"></style>
