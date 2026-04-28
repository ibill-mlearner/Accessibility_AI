<template>
  <!-- Bootstrap grid classes (for example `col-12`, `col-xl-3`, `col-xl-9`) intentionally define responsive layout chunks.
       The shell stacks on small screens and splits into sidebar/content columns on larger breakpoints for consistent navigation ergonomics. -->
  <div v-if="isComponentPreviewRoute" class="container-fluid py-3">
    <router-view />
  </div>
  <div v-else class="app-shell container-fluid py-3">
    <div class="row g-3 app-shell__row">
      <div class="col-12 col-xl-3 app-shell__sidebar">
        <SidebarNav />
      </div>
      <main class="col-12 col-xl-9 d-flex flex-column gap-3 app-shell__main">
        <HeaderBar />
        <p v-if="appError" class="alert alert-danger mb-0">{{ appError }}</p>
        <div class="app-shell__content">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppBootstrapStore } from './stores/appBootstrapStore'
import { useAuthStore } from './stores/authStore'
import { useFeatureStore } from './stores/featureStore'
import SidebarNav from './components/SidebarNav.vue'
import HeaderBar from './components/HeaderBar.vue'

const route = useRoute()
const bootstrap = useAppBootstrapStore()
const auth = useAuthStore()
const featureStore = useFeatureStore()

const isComponentPreviewRoute = computed(() => route.path.startsWith('/component-previews/'))
const appError = computed(() => bootstrap.error || bootstrap.authError)

const fontFamilyByFeature = {
  opendyslexic: 'OpenDyslexic, Arial, sans-serif',
  atkinson: '"Atkinson Hyperlegible", Arial, sans-serif',
  arial: 'Arial, Helvetica, sans-serif',
  verdana: 'Verdana, Geneva, sans-serif',
  monospace: 'ui-monospace, SFMono-Regular, Menlo, monospace'
}

const isEnabledFontSizeFeature = (feature) => (
  Boolean(feature?.enabled)
  && Number.isInteger(Number(feature?.font_size_px))
  && Number(feature?.font_size_px) > 0
)

const isEnabledFontFamilyFeature = (feature) => (
  Boolean(feature?.enabled)
  && typeof feature?.font_family === 'string'
  && feature.font_family.trim().length > 0
)

function applyAccessibilityPresentation(features = []) {
  if (typeof document === 'undefined') {
    return
  }

  const activeFontSize = features.find((feature) => isEnabledFontSizeFeature(feature))
  if (activeFontSize) {
    document.documentElement.style.fontSize = `${Number(activeFontSize.font_size_px)}px`
  } else {
    document.documentElement.style.removeProperty('font-size')
  }

  const activeFontFamily = features.find((feature) => isEnabledFontFamilyFeature(feature))
  const resolvedFontFamily = activeFontFamily
    ? (fontFamilyByFeature[String(activeFontFamily.font_family).trim()] || null)
    : null
  if (resolvedFontFamily) {
    document.documentElement.style.fontFamily = resolvedFontFamily
  } else {
    document.documentElement.style.removeProperty('font-family')
  }
}

watch(
  () => featureStore.features,
  (features) => {
    applyAccessibilityPresentation(Array.isArray(features) ? features : [])
  },
  { deep: true, immediate: true }
)

onMounted(async () => {
  if (!auth.sessionChecked) {
    await auth.me()
  }

  if (auth.isAuthenticated) {
    await bootstrap.bootstrap()
  }
})
</script>

<!-- App-shell layout styling stays in this view-level stylesheet because it defines the top-level design chunks
     (sidebar column, main content column, and shared spacing wrappers) that every routed page sits inside. -->
<style scoped src="./styles/views/app.css"></style>
