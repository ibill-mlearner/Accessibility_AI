import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import LoginView from '../../src/views/LoginView.vue'
import { useAppStore } from '../../src/stores/appStore'

const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    useRouter: () => ({ push })
  }
})

describe('LoginView.vue', () => {
  it('sets role to student and routes home on submit click', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    const wrapper = mount(LoginView)

    await wrapper.find('button.icon-btn').trigger('click')

    expect(store.role).toBe('student')
    expect(push).toHaveBeenCalledWith('/')
  })
})
