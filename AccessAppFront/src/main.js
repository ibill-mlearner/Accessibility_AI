import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
 import { useAppBootstrapStore } from './stores/appBootstrapStore'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

useAppBootstrapStore(pinia)

app.use(router)
app.mount('#app')
