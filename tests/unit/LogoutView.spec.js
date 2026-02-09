import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
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
  it('logs out and routes home when completing logout', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'student'

    const wrapper = mount(LogoutView)
    await wrapper.find('button.btn').trigger('click')

    expect(store.role).toBe('guest')
    expect(push).toHaveBeenCalledWith('/')
  })
})
