<template>
  <section class="profile-view d-flex flex-column gap-3">
    <section class="row g-3">
      <div :class="showAdminModelDownload ? 'col-12 col-xl-7' : 'col-12'">
        <header class="card shadow-sm h-100">
          <div class="card-body d-flex flex-column gap-3">
            <div class="d-flex flex-column flex-md-row align-items-md-start gap-3">
              <div>
                <h2 class="h4 mb-1">Profile</h2>
                <p class="text-muted mb-0">Your activity snapshot across chats and classes.</p>
              </div>
              <ProfileFontSizeSelect
                v-model="selectedFontSize"
                :options="fontSizeOptions"
                @change="applyFontSizePreference"
              />
            </div>

            <ProfileColorblindFeatures
              v-model="selectedColorblindType"
              :options="colorblindOptions"
            />

            <ProfileFontFamilyFeatures
              v-model="selectedFontFamily"
              :options="fontFamilyOptions"
              @change="applyFontFamilyPreference"
            />
          </div>
        </header>
      </div>

      <div v-if="showAdminModelDownload" class="col-12 col-xl-5">
        <ProfileAdminModelDownloadCard @submit="handleAdminModelDownload" />
      </div>
    </section>

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
                {{ visibleEnabledFeatures.length }} enabled
              </p>
              <p v-if="!visibleEnabledFeatures.length" class="mb-0 text-muted">No accessibility features are enabled.</p>
              <ul v-else class="list-group list-group-flush">
                <li
                  v-for="feature in visibleEnabledFeatures"
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
              class="list-group-item px-0 d-flex align-items-center gap-2"
            >
              <span class="badge text-bg-light border">{{ classLabel(course) }}</span>
              <span class="text-truncate">{{ course.name }}</span>
            </li>
          </ul>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { useClassStore } from '../stores/classStore'
import { useFeatureStore } from '../stores/featureStore'
import ProfileFontSizeSelect from '../components/profile/ProfileFontSizeSelect.vue'
import ProfileColorblindFeatures from '../components/profile/ProfileColorblindFeatures.vue'
import ProfileFontFamilyFeatures from '../components/profile/ProfileFontFamilyFeatures.vue'
import ProfileAdminModelDownloadCard from '../components/profile/ProfileAdminModelDownloadCard.vue'

const auth = useAuthStore()
const chatStore = useChatStore()
const classStore = useClassStore()
const featureStore = useFeatureStore()

const isLoading = computed(() => !auth.sessionChecked)
const selectedFontSize = ref('')
const selectedColorblindType = ref('none')
const selectedFontFamily = ref('default')
const colorblindOptions = [
  { value: 'none', label: 'None' },
  { value: 'protanopia', label: 'Protanopia' },
  { value: 'deuteranopia', label: 'Deuteranopia' },
  { value: 'tritanopia', label: 'Tritanopia' },
  { value: 'achromatopsia', label: 'Achromatopsia' }
]

const fontFamilyOptions = [
  { value: 'default', label: 'Default', family: '' },
  { value: 'opendyslexic', label: 'OpenDyslexic', family: 'OpenDyslexic, Arial, sans-serif' },
  { value: 'atkinson', label: 'Atkinson Hyperlegible', family: 'Atkinson Hyperlegible, Arial, sans-serif' },
  { value: 'arial', label: 'Arial', family: 'Arial, Helvetica, sans-serif' },
  { value: 'verdana', label: 'Verdana', family: 'Verdana, Geneva, sans-serif' },
  { value: 'monospace', label: 'Monospace', family: 'ui-monospace, SFMono-Regular, Menlo, monospace' }
]
const currentUserId = computed(() => auth.currentUser?.id ?? auth.user?.id ?? null)
const normalizedRole = computed(() => String(auth.role || '').toLowerCase())
const allowedActions = computed(() => new Set(auth.allowedActions || []))
const canTeachClasses = computed(() =>
  (normalizedRole.value === 'instructor' || normalizedRole.value === 'admin')
  && allowedActions.value.has('classes:write')
)
const showAdminModelDownload = computed(() =>
  normalizedRole.value === 'admin'
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
const isFontSizeFeature = (feature) => {
  if (feature?.font_size_px === null || feature?.font_size_px === undefined || feature?.font_size_px === '') {
    return false
  }
  const numericSize = Number(feature.font_size_px)
  return Number.isInteger(numericSize) && numericSize > 0
}
const isFontFamilyFeature = (feature) => Boolean(feature?.font_family)
const isColorFamilyFeature = (feature) => Boolean(feature?.color_family)
const isDisplayableFeature = (feature) => feature?.displayable !== false
const enabledFeatures = computed(() => featureStore.features.filter((feature) => feature?.enabled))
const fontSizeFeatures = computed(() =>
  featureStore.features
    .filter((feature) => isFontSizeFeature(feature))
    .sort((left, right) => Number(left.font_size_px) - Number(right.font_size_px))
)
const fontFamilyFeatures = computed(() =>
  featureStore.features
    .filter((feature) => isFontFamilyFeature(feature))
)
const fontSizeOptions = computed(() =>
  fontSizeFeatures.value.map((feature) => ({
    value: String(feature.font_size_px),
    label: `${feature.font_size_px}px`
  }))
)
const visibleEnabledFeatures = computed(() =>
  enabledFeatures.value.filter((feature) =>
    !feature?.skipInProfile
    && isDisplayableFeature(feature)
    && !isFontSizeFeature(feature)
    && !isFontFamilyFeature(feature)
    && !isColorFamilyFeature(feature)
  )
)

watch(
  () => featureStore.features,
  (features) => {
    const activeFontSize = features.find(
      (feature) => feature?.enabled && isFontSizeFeature(feature)
    )
    selectedFontSize.value = activeFontSize
      ? String(activeFontSize.font_size_px)
      : (fontSizeOptions.value[0]?.value ?? '')
  },
  { immediate: true, deep: true }
)

watch(
  () => featureStore.features,
  (features) => {
    const activeFontFamily = features.find(
      (feature) => feature?.enabled && isFontFamilyFeature(feature)
    )
    selectedFontFamily.value = activeFontFamily?.font_family || 'default'
  },
  { immediate: true, deep: true }
)

watch(
  selectedFontSize,
  (value) => {
    if (!value) {
      document.documentElement.style.removeProperty('font-size')
      return
    }
    document.documentElement.style.fontSize = `${Number(value)}px`
  },
  { immediate: true }
)

watch(
  selectedFontFamily,
  (value) => {
    const selected = fontFamilyOptions.find((option) => option.value === value)
    if (!selected?.family) {
      document.documentElement.style.removeProperty('font-family')
      return
    }
    document.documentElement.style.fontFamily = selected.family
  },
  { immediate: true }
)

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

async function applyFontSizePreference() {
  const selectedValue = Number(selectedFontSize.value)
  if (!Number.isFinite(selectedValue) || selectedValue <= 0) {
    return
  }
  const updates = fontSizeFeatures.value.map((feature) => ({
    accommodation_id: Number(feature.id),
    enabled: Number(feature.font_size_px) === selectedValue
  }))
  await featureStore.replaceFeaturePreferences(updates)
}

async function applyFontFamilyPreference() {
  const selectedValue = String(selectedFontFamily.value || '').trim()
  const updates = fontFamilyFeatures.value.map((feature) => ({
    accommodation_id: Number(feature.id),
    enabled: selectedValue !== 'default' && String(feature.font_family) === selectedValue
  }))
  await featureStore.replaceFeaturePreferences(updates)
}

async function handleAdminModelDownload(modelId) {
  // Wiring point for AI pipeline model download workflow.
  await Promise.resolve(modelId)
}
</script>

<style scoped src="../styles/views/profile-view.css"></style>
