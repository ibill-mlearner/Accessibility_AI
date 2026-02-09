import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import AccessibilityView from './views/AccessibilityView.vue'
import SavedNotesView from './views/SavedNotesView.vue'
import ClassesView from './views/ClassesView.vue'
import LoginView from './views/LoginView.vue'
import LogoutView from './views/LogoutView.vue'
import ErrorView from './views/ErrorView.vue'
import HeaderBarPreview from './views/component_previews/HeaderBarPreview.vue'
import SidebarNavPreview from './views/component_previews/SidebarNavPreview.vue'
import LoginFormCardPreview from './views/component_previews/LoginFormCardPreview.vue'
import ChatBubbleCardPreview from './views/component_previews/ChatBubbleCardPreview.vue'
import ComposerBarPreview from './views/component_previews/ComposerBarPreview.vue'
import ClassOptionCardPreview from './views/component_previews/ClassOptionCardPreview.vue'
import FeatureOptionCardPreview from './views/component_previews/FeatureOptionCardPreview.vue'
import SavedNoteCardPreview from './views/component_previews/SavedNoteCardPreview.vue'
import OptionCardPreview from './views/component_previews/OptionCardPreview.vue'
import OptionSelectorPreview from './views/component_previews/OptionSelectorPreview.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/accessibility', name: 'accessibility', component: AccessibilityView },
  { path: '/saved-notes', name: 'saved-notes', component: SavedNotesView },
  { path: '/classes/:role', name: 'classes', component: ClassesView, props: true },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/logout', name: 'logout', component: LogoutView },
  { path: '/error', name: 'error', component: ErrorView },
  { path: '/component-previews/header-bar', name: 'preview-header-bar', component: HeaderBarPreview },
  { path: '/component-previews/sidebar-nav', name: 'preview-sidebar-nav', component: SidebarNavPreview },
  { path: '/component-previews/login-form-card', name: 'preview-login-form-card', component: LoginFormCardPreview },
  { path: '/component-previews/chat-bubble-card', name: 'preview-chat-bubble-card', component: ChatBubbleCardPreview },
  { path: '/component-previews/composer-bar', name: 'preview-composer-bar', component: ComposerBarPreview },
  { path: '/component-previews/class-option-card', name: 'preview-class-option-card', component: ClassOptionCardPreview },
  { path: '/component-previews/feature-option-card', name: 'preview-feature-option-card', component: FeatureOptionCardPreview },
  { path: '/component-previews/saved-note-card', name: 'preview-saved-note-card', component: SavedNoteCardPreview },
  { path: '/component-previews/option-card', name: 'preview-option-card', component: OptionCardPreview },
  { path: '/component-previews/option-selector', name: 'preview-option-selector', component: OptionSelectorPreview }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
