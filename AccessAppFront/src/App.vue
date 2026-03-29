  <template>
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
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppBootstrapStore } from './stores/appBootstrapStore'
import { useAuthStore } from './stores/authStore'
import SidebarNav from './components/SidebarNav.vue'
import HeaderBar from './components/HeaderBar.vue'

const route = useRoute()
const bootstrap = useAppBootstrapStore()
const auth = useAuthStore()

const isComponentPreviewRoute = computed(() => route.path.startsWith('/component-previews/'))
const appError = computed(() => bootstrap.error || bootstrap.authError)

onMounted(async () => {
  if (!auth.sessionChecked) {
    await auth.me()
  }

  if (auth.isAuthenticated) {
    await bootstrap.bootstrap()
  }
})
</script>

<style scoped>
.app-shell {
  height: 100dvh;
  overflow: hidden;
}

.app-shell__row,
.app-shell__sidebar,
.app-shell__main {
  height: 100%;
  min-height: 0;
}

.app-shell__main {
  overflow: hidden;
}

.app-shell__content {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
