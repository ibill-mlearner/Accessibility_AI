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

      <section class="row g-3">
        <div class="col-12 col-xl-7">
          <section class="card shadow-sm h-100">
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
        </div>

        <div class="col-12 col-xl-5">
          <section class="card shadow-sm h-100">
            <div class="card-body d-flex flex-column gap-2">
              <h3 class="h6 text-uppercase text-muted mb-1">Accessibility features</h3>
              <p class="mb-0 text-muted small">
                {{ enabledFeatures.length }} enabled
              </p>
              <p v-if="!enabledFeatures.length" class="mb-0 text-muted">No accessibility features are enabled.</p>
              <ul v-else class="list-group list-group-flush">
                <li
                  v-for="feature in enabledFeatures"
                  :key="feature.id"
                  class="list-group-item px-0"
                >
                  {{ feature.name || feature.title || `Feature #${feature.id}` }}
                </li>
              </ul>
            </div>
          </section>
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
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { useClassStore } from '../stores/classStore'
import { useFeatureStore } from '../stores/featureStore'

const auth = useAuthStore()
const chatStore = useChatStore()
const classStore = useClassStore()
const featureStore = useFeatureStore()

const isLoading = computed(() => !auth.sessionChecked)
const currentUserId = computed(() => auth.currentUser?.id ?? auth.user?.id ?? null)
const normalizedRole = computed(() => String(auth.role || '').toLowerCase())
const allowedActions = computed(() => new Set(auth.allowedActions || []))
const canTeachClasses = computed(() =>
  (normalizedRole.value === 'instructor' || normalizedRole.value === 'admin')
  && allowedActions.value.has('classes:write')
)

const teachingClasses = computed(() =>
  classStore.classes.filter((course) => Number(course?.instructor_id) === Number(currentUserId.value))
)
const classesImIn = computed(() =>
  classStore.classes.filter((course) => Number(course?.instructor_id) !== Number(currentUserId.value))
)

const metrics = computed(() => {
  const items = [
    { label: 'Total chats', value: chatStore.chats.length },
    { label: "Classes I'm in", value: classesImIn.value.length }
  ]

  if (canTeachClasses.value) {
    items.push({ label: 'Classes teaching', value: teachingClasses.value.length })
  }

  return items
})

const recentChats = computed(() => chatStore.chats.slice(0, 5))
const enabledFeatures = computed(() => featureStore.features.filter((feature) => feature?.enabled))

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

  if (auth.isAuthenticated && !featureStore.features.length) {
    await featureStore.fetchFeatures().catch(() => {})
  }
})

function classLabel(course) {
  return Number(course?.instructor_id) === Number(currentUserId.value) ? 'Instructor' : 'Member'
}
</script>
