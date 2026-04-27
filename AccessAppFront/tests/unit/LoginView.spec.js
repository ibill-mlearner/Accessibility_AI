import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LoginView from '../../src/views/LoginView.vue'

const push = vi.fn()
const login = vi.fn()
const bootstrap = vi.fn()
const prepareNewChat = vi.fn()
const authState = { authError: '', login }

vi.mock('../../src/stores/authStore', () => ({
  useAuthStore: () => authState
}))

vi.mock('../../src/stores/appBootstrapStore', () => ({
  useAppBootstrapStore: () => ({ bootstrap })
}))

vi.mock('../../src/stores/chatStore', () => ({
  useChatStore: () => ({ prepareNewChat })
}))

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return { ...mod, useRouter: () => ({ push }), useRoute: () => ({ query: {} }) }
})

describe('LoginView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authState.authError = ''
    window.sessionStorage.clear()
  })

  it('routes home after a successful login without persisting sessionStorage', async () => {
    login.mockResolvedValueOnce(true)
    bootstrap.mockResolvedValueOnce()
    const wrapper = mount(LoginView)

    await wrapper.find('input[placeholder="Email . . ."]').setValue('student@example.com')
    await wrapper.find('input[type="password"]').setValue('secret')
    await wrapper.find('button.btn.btn-primary').trigger('click')
    await flushPromises()

    expect(login).toHaveBeenCalledWith({ email: 'student@example.com', password: 'secret' })
    expect(bootstrap).toHaveBeenCalled()
    expect(prepareNewChat).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ path: '/', query: {} })
    expect(window.sessionStorage.getItem('accessapp:session')).toBeNull()
  })

  it('shows auth error and avoids session persistence when login fails', async () => {
    login.mockImplementationOnce(async () => {
      authState.authError = 'Invalid email or password.'
      throw new Error('Unauthorized')
    })
    const wrapper = mount(LoginView)

    await wrapper.find('input[placeholder="Email . . ."]').setValue('bad@example.com')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('button.btn.btn-primary').trigger('click')
    await flushPromises()

    expect(login).toHaveBeenCalledWith({ email: 'bad@example.com', password: 'wrong' })
    expect(push).not.toHaveBeenCalled()
    expect(bootstrap).not.toHaveBeenCalled()
    expect(prepareNewChat).not.toHaveBeenCalled()
    expect(window.sessionStorage.getItem('accessapp:session')).toBeNull()
  })
})
