import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import AccessibilityView from './views/AccessibilityView.vue'
import SavedNotesView from './views/SavedNotesView.vue'
import ClassesView from './views/ClassesView.vue'
import LoginView from './views/LoginView.vue'
import LogoutView from './views/LogoutView.vue'
import ErrorView from './views/ErrorView.vue'
import ProfileView from './views/ProfileView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/accessibility', name: 'accessibility', component: AccessibilityView },
  { path: '/saved-notes', name: 'saved-notes', component: SavedNotesView },
  { path: '/classes/:role', name: 'classes', component: ClassesView, props: true },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/logout', name: 'logout', component: LogoutView },
  { path: '/profile', name: 'profile', component: ProfileView },
  { path: '/error', name: 'error', component: ErrorView },
  { path: '/:pathMatch(.*)*', name: 'not-found', redirect: '/error' }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
