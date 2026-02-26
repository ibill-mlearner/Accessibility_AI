import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
// import { useAppStore } from './stores/appStore'
 import { useAppBootstrapStore } from './stores/appBootstrapStore'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

useAppBootstrapStore(pinia)

// const store = useAppStore(pinia)
// store.hydrateSession()
// Not ready to remove hydration, refreshing the page loses authentication
// useAppStore(pinia)
// Restore client-mirrored auth context from sessionStorage before first route render.

app.use(router)
app.mount('#app')
