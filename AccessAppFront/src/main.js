import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAppStore } from './stores/appStore'
import './styles.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const store = useAppStore(pinia)
store.hydrateSession()
// Restore client-mirrored auth context from sessionStorage before first route render.

app.use(router)
app.mount('#app')
