import { defineStore } from 'pinia'
import { useChatStore } from './chatStore'
import { useClassStore } from './classStore'
import { useNoteStore } from './noteStore'
import { useAuthStore } from './authStore'
import { useFeatureStore } from './featureStore'

export const useAppBootstrapStore = defineStore('appBootstrap', {
  state: () => ({
    loading: false,
    error: '',
    authError: ''
  }),
  actions: {
    async bootstrap() {
      this.loading = true
      this.error = ''
      this.authError = ''

      const auth = useAuthStore()
      if (!auth.sessionChecked) {
        await auth.me()
      }

      if (!auth.isAuthenticated) {
        this.loading = false
        return
      }

      const chats = useChatStore()
      const classes = useClassStore()
      const notes = useNoteStore()
      const features = useFeatureStore()

      const results = await Promise.allSettled([
        chats.fetchChats(),
        classes.fetchClasses(),
        notes.fetchNotes(),
        features.fetchFeatures()
      ])

      const failures = results
        .filter((r) => r.status === 'rejected')
        .map((r) => r.reason)

      if (failures.some((e) => e?.kind === 'auth')) {
        this.authError = 'Your session is invalid or expired. Please sign in again.'
        auth.logout()
      }

      if (failures.some((e) => e?.kind && e.kind !== 'auth')) {
        this.error = 'Some application resources could not be loaded from the backend service.'
      }

      this.loading = false
    }
  }
})