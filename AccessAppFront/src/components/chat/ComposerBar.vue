<template>
  <div class="card shadow-sm">
    <div
      class="card-body d-grid"
      :style="{
        gridTemplateColumns: showLogin
          ? 'auto auto 1fr 20%'
          : 'auto 1fr 20%',
        gap: '8px',
        alignItems: 'center'
      }"
    >
      <button v-if="showLogin"
        class="btn btn-outline-secondary" 
        @click="$emit('login')">Login</button>
      <button class="btn btn-primary" 
        @click="$emit('send')">➤</button>
      <input
        class="form-control"
        :placeholder="placeholder"
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <select
        v-if="showModelSelect"
        class="form-select"
        :value="selectedModel"
        @change="$emit('update:selectedModel', $event.target.value)"
      >
        <option>Model selection . . .</option>
        <option>General</option>
        <option>Lecture Assistant</option>
      </select>
    </div>
  </div>
</template>

<script setup>
defineProps({
  showLogin: { type: Boolean, default: false },
  showModelSelect: { type: Boolean, default: true },
  placeholder: { type: String, default: 'Type here . . .' },
  modelValue: { type: String, default: '' },
  selectedModel: { type: String, default: 'General' }
})

defineEmits(['login', 'send', 'update:modelValue', 'update:selectedModel'])
</script>
