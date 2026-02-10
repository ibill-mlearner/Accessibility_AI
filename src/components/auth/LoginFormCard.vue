<template>
  <section class="auth-card">
    <input
      :value="username"
      @input="$emit('update:username', $event.target.value)"
      placeholder="Username . . ."
      aria-label="Username"
      autocomplete="username"
      required
    />
    <p v-if="showValidation && usernameError" class="auth-error">{{ usernameError }}</p>

    <input
      :value="password"
      @input="$emit('update:password', $event.target.value)"
      type="password"
      placeholder="Password . . ."
      aria-label="Password"
      autocomplete="current-password"
      required
    />
    <p v-if="showValidation && passwordError" class="auth-error">{{ passwordError }}</p>

    <button class="icon-btn" @click="handleSubmit">➤</button>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  username: { type: String, default: '' },
  password: { type: String, default: '' }
})

const emit = defineEmits(['submit', 'update:username', 'update:password'])

const showValidation = ref(false)

const usernameError = computed(() => {
  if (!props.username.trim()) return 'Username is required.'
  if (props.username.trim().length < 3) return 'Username must be at least 3 characters.'
  return ''
})

const passwordError = computed(() => {
  if (!props.password.trim()) return 'Password is required.'
  if (props.password.length < 6) return 'Password must be at least 6 characters.'
  return ''
})

function handleSubmit() {
  showValidation.value = true
  if (usernameError.value || passwordError.value) return
  emit('submit')
}
</script>
