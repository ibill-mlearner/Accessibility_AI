import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LoginView from '../../src/views/LoginView.vue'
import api from '../../src/services/api'

const push = vi.fn()
const mockedRoute = {
  query: {}
}

vi.mock('../../src/services/api', () => ({
  default: {
    post: vi.fn()
  }
}))

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    useRouter: () => ({ push }),
    useRoute: () => mockedRoute
  }
})

describe('LoginView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    window.sessionStorage.clear()
    mockedRoute.query = {}
  })

  it('routes home only after login API success and persists session', async () => {
    let resolveLogin
    api.post.mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve
      })
    )

    const wrapper = mount(LoginView)

    await wrapper.find('input[placeholder="Username . . ."]').setValue('student@example.com')
    await wrapper.find('input[type="password"]').setValue('secret')
    await wrapper.find('button.icon-btn').trigger('click')

    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      email: 'student@example.com',
      password: 'secret'
    })
    expect(push).not.toHaveBeenCalled()

    resolveLogin({ data: { user: { id: 7, email: 'student@example.com', role: 'student' } } })
    await flushPromises()

    expect(push).toHaveBeenCalledWith({ path: '/', query: {} })
    const persisted = JSON.parse(window.sessionStorage.getItem('accessapp:session'))
    expect(persisted).toMatchObject({
      role: 'student',
      currentUser: { id: 7, email: 'student@example.com' },
      isAuthenticated: true
    })
  })

  it('stays on login, shows auth error, and does not persist session when login fails', async () => {
    api.post.mockRejectedValue({ response: { status: 401 } })

    const wrapper = mount(LoginView)

    await wrapper.find('input[placeholder="Username . . ."]').setValue('bad@example.com')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('button.icon-btn').trigger('click')
    await flushPromises()

    expect(push).not.toHaveBeenCalled()
    expect(window.sessionStorage.getItem('accessapp:session')).toBeNull()
    expect(wrapper.find('.auth-error').exists()).toBe(true)
    expect(wrapper.find('.auth-error').text()).toContain('Invalid email or password.')
  })

  it('returns to requested path and restores prompt from query after login', async () => {
    mockedRoute.query = {
      next: '/',
      prompt: 'Need this after login'
    }

    api.post.mockResolvedValue({
      data: { user: { id: 9, email: 'student@example.com', role: 'student' } }
    })

    const wrapper = mount(LoginView)
    await wrapper.find('input[placeholder="Username . . ."]').setValue('student@example.com')
    await wrapper.find('input[type="password"]').setValue('secret')
    await wrapper.find('button.icon-btn').trigger('click')
    await flushPromises()

    expect(push).toHaveBeenCalledWith({ path: '/', query: { prompt: 'Need this after login' } })
  })
})
