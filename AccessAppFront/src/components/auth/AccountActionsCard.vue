<template>
  <section v-if="isLoggedIn" class="card shadow-sm">
    <div class="card-body d-grid">
      <ProfileButton @profile="$emit('profile')" />
      <LogoutButton @logout="$emit('logout')" />
    </div>
  </section>
</template>

<script setup>
import LogoutButton from './LogoutButton.vue'
import ProfileButton from './ProfileButton.vue'

defineProps({
  isLoggedIn: { type: Boolean, default: false }
})

defineEmits(['profile', 'logout'])
</script>

<style scoped>
.account-actions-card {
  flex: 0 0 auto;
}

.account-actions-card__buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
</style>
