<template>
  <section class="card shadow-sm" style="max-width: 540px">
    <div class="card-body d-grid" style="grid-template-columns: 1fr 1fr auto; gap: 8px">
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
