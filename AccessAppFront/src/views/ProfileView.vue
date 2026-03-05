<template>
  <section class="card shadow-sm">
    <div class="card-body d-flex flex-column gap-3">
      <header>
        <h2 class="h4 mb-1">Profile</h2>
        <p class="text-muted mb-0">Your account and session details.</p>
      </header>

      <p v-if="isLoading" class="mb-0 text-muted">Loading profile details . . .</p>
      <p v-else-if="auth.authError" class="alert alert-warning mb-0">{{ auth.authError }}</p>

      <template v-if="!isLoading">
        <ProfileHeaderCard :user="user" :role="role" :is-authenticated="auth.isAuthenticated" />

        <ProfileSessionCard
          :session="auth.session"
          :allowed-actions="auth.allowedActions"
        />

        <ProfileSecurityCard @logout="handleLogout" @retry="refreshSession" />

        <ProfileEmptyState
          v-if="!auth.isAuthenticated || !user"
          @retry="refreshSession"
        />
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import ProfileHeaderCard from '../components/profile/ProfileHeaderCard.vue'
import ProfileSessionCard from '../components/profile/ProfileSessionCard.vue'
import ProfileSecurityCard from '../components/profile/ProfileSecurityCard.vue'
import ProfileEmptyState from '../components/profile/ProfileEmptyState.vue'

const router = useRouter()
const auth = useAuthStore()

const isLoading = computed(() => !auth.sessionChecked)
const user = computed(() => auth.currentUser || auth.user)
const role = computed(() => auth.role || 'guest')

onMounted(async () => {
  if (!auth.sessionChecked) {
    await auth.me()
  }
})

async function refreshSession() {
  await auth.me()
}

async function handleLogout() {
  await auth.logout()
  await router.push('/')
}
</script>
