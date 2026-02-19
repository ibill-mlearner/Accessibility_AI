import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAppStore } from './stores/appStore'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const store = useAppStore(pinia)
// store.hydrateSession()
useAppStore(pinia)
// Restore client-mirrored auth context from sessionStorage before first route render.

app.use(router)
app.mount('#app')
