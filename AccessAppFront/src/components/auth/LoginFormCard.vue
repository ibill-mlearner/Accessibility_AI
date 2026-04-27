<template>
  <section class="card shadow-sm login-form-card">
    <div class="card-body d-grid login-form-card__body">
      <input
        class="form-control"
        :value="email"
        @input="$emit('update:email', $event.target.value)"
        type="email"
        placeholder="Email . . ."
      />
      <input
        class="form-control"
        :value="password"
        @input="$emit('update:password', $event.target.value)"
        type="password"
        placeholder="Password . . ."
      />
      <button class="btn btn-primary" @click="$emit('submit')">➤</button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  email: { type: String, default: '' },
  password: { type: String, default: '' }
})

defineEmits(['submit', 'update:email', 'update:password'])
</script>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../../styles/components/auth/login-form-card.css"></style>
