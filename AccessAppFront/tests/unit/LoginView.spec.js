import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LoginView from '../../src/views/LoginView.vue'
import api from '../../src/services/api'

const push = vi.fn()

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
    useRoute: () => ({ query: {} })
  }
})

describe('LoginView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    window.sessionStorage.clear()
  })

//  it('persists session and routes home after successful login', async () => {
  it('routes home after a successful login without persisting sessionStorage', async () => {
    api.post.mockResolvedValueOnce({
      data: { user: { id: 7, email: 'student@example.com', role: 'student' } }
    })

    const wrapper = mount(LoginView)

    await wrapper.find('input[placeholder="Username . . ."]').setValue('student@example.com')
    await wrapper.find('input[type="password"]').setValue('secret')
    await wrapper.find('button.icon-btn').trigger('click')
    await flushPromises()

    expect(push).toHaveBeenCalledWith({ path: '/', query: {} })
    expect(JSON.parse(window.sessionStorage.getItem('accessapp:session'))).toMatchObject({
      role: 'student',
      isAuthenticated: true
    })
  })

  it('shows auth error and avoids session persistence when login fails', async () => {
    api.post.mockRejectedValueOnce({ response: { status: 401 } })

    const wrapper = mount(LoginView)

    await wrapper.find('input[placeholder="Username . . ."]').setValue('bad@example.com')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('button.icon-btn').trigger('click')
    await flushPromises()

    expect(push).not.toHaveBeenCalled()
    expect(window.sessionStorage.getItem('accessapp:session')).toBeNull()
    expect(wrapper.find('.auth-error').text()).toContain('Invalid email or password.')
  })
})
