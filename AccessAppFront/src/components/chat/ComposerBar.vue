<template>
  <div class="card shadow-sm">
    <div
      class="card-body d-grid composer-bar__grid"
      :class="showLogin ? 'composer-bar__grid--with-login' : 'composer-bar__grid--no-login'"
    >
      <button
        v-if="showLogin"
        class="btn btn-outline-secondary"
        @click="$emit('login')"
      >Login</button>
      <button
        class="btn btn-primary"
        :disabled="sendDisabled"
        @click="$emit('send')"
      >➤</button>
      <input
        class="form-control"
        :placeholder="placeholder"
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.enter="handleEnterKey"
      />
      <select
        v-if="showModelSelect"
        class="form-select"
        :disabled="modelLoading || !modelOptions.length"
        :value="selectedModel"
        @change="$emit('update:selected-model', $event.target.value)"
      >
        <option value="" disabled> {{ modelLoading ? 'Loading models...' : 'Select a model' }}</option>
        <option
          v-for="option in modelOptions"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const emit = defineEmits(['login', 'send', 'update:modelValue', 'update:selected-model'])
const props = defineProps({
  showLogin: { type: Boolean, default: false },
  showModelSelect: { type: Boolean, default: true },
  placeholder: { type: String, default: 'Type here . . .' },
  modelValue: { type: String, default: '' },
  selectedModel: { type: String, default: '' },
  modelOptions: { type: Array, default: () => [] },
  modelLoading: { type: Boolean, default: false }
})

const sendDisabled = computed(() => {
  return props.showModelSelect && (props.modelLoading || !String(props.selectedModel || '').trim())
})

const handleEnterKey = (event) => {
  if (event.shiftKey) return

  event.preventDefault()
  if (!sendDisabled.value) {
    emit('send')
  }
}
</script>

<style scoped src="../../styles/components/chat/composer-bar.css"></style>
