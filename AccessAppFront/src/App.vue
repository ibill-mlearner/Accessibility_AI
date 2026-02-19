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
        <p v-if="store.error" class="alert alert-danger mb-0">{{ store.error }}</p>
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from './stores/appStore'
import SidebarNav from './components/SidebarNav.vue'
import HeaderBar from './components/HeaderBar.vue'

const route = useRoute()
const store = useAppStore()

const isComponentPreviewRoute = computed(() => route.path.startsWith('/component-previews/'))

onMounted(() => {
  store.bootstrap()
})
</script>
