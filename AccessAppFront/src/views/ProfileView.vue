<template>
  <section class="d-flex flex-column gap-3">
    <header class="card shadow-sm">
      <div class="card-body">
        <h2 class="h4 mb-1">Profile</h2>
        <p class="text-muted mb-0">Your activity snapshot across chats and classes.</p>
      </div>
    </header>

    <p v-if="isLoading" class="mb-0 text-muted">Loading profile details . . .</p>
    <p v-else-if="auth.authError" class="alert alert-warning mb-0">{{ auth.authError }}</p>

    <template v-if="!isLoading && auth.isAuthenticated">
      <section class="card shadow-sm">
        <div class="card-body">
          <h3 class="h6 text-uppercase text-muted mb-3">Overview</h3>
          <div class="row g-2">
            <div class="col-12 col-md-6 col-xl-3" v-for="metric in metrics" :key="metric.label">
              <article class="border rounded-3 p-3 h-100 bg-light-subtle">
                <p class="text-muted small mb-1">{{ metric.label }}</p>
                <p class="h4 mb-0">{{ metric.value }}</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section class="card shadow-sm">
        <div class="card-body d-flex flex-column gap-2">
          <h3 class="h6 text-uppercase text-muted mb-1">Recent chats</h3>
          <p v-if="!chatStore.chats.length" class="mb-0 text-muted">No chats yet.</p>
          <ul v-else class="list-group list-group-flush">
            <li
              v-for="chat in recentChats"
              :key="chat.id"
              class="list-group-item px-0 d-flex justify-content-between gap-3"
            >
              <span class="text-truncate">{{ chat.title || 'Untitled chat' }}</span>
              <span class="text-muted small">Class #{{ chat.class_id ?? 'n/a' }}</span>
            </li>
          </ul>
        </div>
      </section>

      <section class="card shadow-sm">
        <div class="card-body d-flex flex-column gap-2">
          <h3 class="h6 text-uppercase text-muted mb-1">Class footprint</h3>
          <p v-if="!classStore.classes.length" class="mb-0 text-muted">No classes loaded.</p>
          <ul v-else class="list-group list-group-flush">
            <li
              v-for="course in classStore.classes.slice(0, 5)"
              :key="course.id"
              class="list-group-item px-0 d-flex justify-content-between gap-3"
            >
              <span class="text-truncate">{{ course.name }}</span>
              <span class="badge text-bg-light border">{{ classLabel(course) }}</span>
            </li>
          </ul>
        </div>
      </section>

      <ProfileSecurityCard @logout="handleLogout" @retry="refreshSession" />
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { useClassStore } from '../stores/classStore'
import ProfileSecurityCard from '../components/profile/ProfileSecurityCard.vue'

const router = useRouter()
const auth = useAuthStore()
const chatStore = useChatStore()
const classStore = useClassStore()

const isLoading = computed(() => !auth.sessionChecked)
const currentUserId = computed(() => auth.currentUser?.id ?? auth.user?.id ?? null)
const teachingClasses = computed(() =>
  classStore.classes.filter((course) => Number(course?.instructor_id) === Number(currentUserId.value))
)
const chatsByClassCount = computed(() => {
  const usedClassIds = new Set(chatStore.chats.map((chat) => chat?.class_id).filter(Boolean))
  return usedClassIds.size
})

const metrics = computed(() => [
  { label: 'Total chats', value: chatStore.chats.length },
  { label: 'Active conversation', value: chatStore.hasActiveChat ? 'Yes' : 'No' },
  { label: 'Classes loaded', value: classStore.classes.length },
  { label: 'Classes teaching', value: teachingClasses.value.length },
  { label: 'Classes with chats', value: chatsByClassCount.value },
  { label: 'Allowed actions', value: auth.allowedActions.length }
])

const recentChats = computed(() => chatStore.chats.slice(0, 5))

onMounted(async () => {
  if (!auth.sessionChecked) {
    await auth.me()
  }

  if (auth.isAuthenticated && !chatStore.chats.length) {
    await chatStore.fetchChats().catch(() => {})
  }

  if (auth.isAuthenticated && !classStore.classes.length) {
    await classStore.fetchClasses().catch(() => {})
  }
})

async function refreshSession() {
  await auth.me()
  if (auth.isAuthenticated) {
    await Promise.allSettled([chatStore.fetchChats(), classStore.fetchClasses()])
  }
}

function classLabel(course) {
  return Number(course?.instructor_id) === Number(currentUserId.value) ? 'Instructor' : 'Member'
}

async function handleLogout() {
  await auth.logout()
  await router.push('/')
}
</script>
