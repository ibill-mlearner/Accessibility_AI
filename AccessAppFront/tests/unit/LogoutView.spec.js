import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LogoutView from '../../src/views/LogoutView.vue'
import { useAppStore } from '../../src/stores/appStore'

const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    useRouter: () => ({ push })
  }
})

describe('LogoutView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockReset()
    window.sessionStorage.clear()
  })

  it('logs out, clears persisted session, and routes home immediately on mount', async () => {
    const store = useAppStore()
    store.role = 'student'
    store.currentUser = { id: 9, email: 'student@example.com' }
    store.user = store.currentUser
    store.isAuthenticated = true
    store.persistSession()

    mount(LogoutView)

    expect(store.role).toBe('guest')
    expect(store.currentUser).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(window.sessionStorage.getItem('accessapp:session')).toBeNull()
    expect(push).toHaveBeenCalledWith('/')
  })
})
