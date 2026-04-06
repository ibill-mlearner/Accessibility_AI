<template>
  <section v-if="isLoggedIn" class="card shadow-sm account-actions-card">
    <div class="card-body d-grid account-actions-card__buttons">
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

<style scoped src="../../styles/components/auth/account-actions-card.css"></style>
