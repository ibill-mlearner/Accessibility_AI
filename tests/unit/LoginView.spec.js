import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi, beforeEach } from 'vitest'
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
  beforeEach(() => {
    push.mockReset()
  })

  it('routes home on successful submit', async () => {
    setActivePinia(createPinia())
    const wrapper = mount(LoginView)

    const [userInput, passInput] = wrapper.findAll('input')
    await userInput.setValue('student')
    await passInput.setValue('student123')
    await wrapper.find('button.icon-btn').trigger('click')

    expect(push).toHaveBeenCalledWith('/')
  })

  it('routes to error page when login fails', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    const loginSpy = vi.spyOn(store, 'login').mockRejectedValue(new Error('Invalid credentials'))
    const wrapper = mount(LoginView)

    const [userInput, passInput] = wrapper.findAll('input')
    await userInput.setValue('student')
    await passInput.setValue('wrongpass')
    await wrapper.find('button.icon-btn').trigger('click')

    expect(loginSpy).toHaveBeenCalledWith('student', 'wrongpass')
    expect(push).toHaveBeenCalledWith('/error')
  })
})
