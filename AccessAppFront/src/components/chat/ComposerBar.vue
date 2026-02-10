<template>
  <div class="composer-row">
    <button v-if="showLogin" class="btn" @click="$emit('login')">Login</button>
    <button class="icon-btn" @click="$emit('send')">➤</button>
    <input :placeholder="placeholder" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />
    <select v-if="showModelSelect" :value="selectedModel" @change="$emit('update:selectedModel', $event.target.value)">
      <option>Model selection . . .</option>
      <option>General</option>
      <option>Lecture Assistant</option>
    </select>
  </div>
</template>

<script setup>
defineProps({
  showLogin: { type: Boolean, default: false },
  showModelSelect: { type: Boolean, default: true },
  placeholder: { type: String, default: 'Type here . . .' },
  modelValue: { type: String, default: '' },
  selectedModel: { type: String, default: '' }
})

defineEmits(['login', 'send', 'update:modelValue', 'update:selectedModel'])
</script>
