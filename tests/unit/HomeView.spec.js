import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import HomeView from '../../src/views/HomeView.vue'
import { useAppStore } from '../../src/stores/appStore'

const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    useRouter: () => ({ push })
  }
})

describe('HomeView.vue', () => {
  it('shows login button for guest and routes to login', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'guest'

    const wrapper = mount(HomeView)
    const loginBtn = wrapper.find('button.btn')
    expect(loginBtn.exists()).toBe(true)

    await loginBtn.trigger('click')
    expect(push).toHaveBeenCalledWith('/login')
  })
})
