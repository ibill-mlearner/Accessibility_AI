  <template>
    <div v-if="isComponentPreviewRoute" class="container-fluid py-3">
    <router-view />
  </div>
  <div v-else class="app-shell container-fluid py-3">
    <div class="row g-3">
      <div class="col-12 col-xl-3">
        <SidebarNav />
      </div>
      <main class="col-12 col-xl-9 d-flex flex-column gap-3">
        <HeaderBar />
        <p v-if="appError" class="alert alert-danger mb-0">{{ appError }}</p>
        <router-view />
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
