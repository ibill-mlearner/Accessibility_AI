import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import HomeView from '../../src/views/HomeView.vue'
import { useAppStore } from '../../src/stores/appStore'

const push = vi.fn()
const replace = vi.fn()
const mockedRoute = {
  path: '/',
  query: {}
}

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    useRouter: () => ({ push, replace }),
    useRoute: () => mockedRoute
  }
})

describe('HomeView.vue', () => {
  it('redirects guests to login with prompt when send is clicked', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'guest'
    push.mockClear()

    const wrapper = mount(HomeView)
    await wrapper.find('input').setValue('Need help with week 1 summary')
    await wrapper.find('button.icon-btn').trigger('click')

    expect(push).toHaveBeenCalledWith({
      path: '/login',
      query: {
        next: '/',
        prompt: 'Need help with week 1 summary'
      }
    })
    expect(wrapper.find('.chat-error-banner').text()).toContain('Please log in to send a prompt.')
  })

  it('shows login button for guest and routes to login', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'guest'

    const wrapper = mount(HomeView)
    const loginBtn = wrapper.findAll('button').find((button) => button.text() === 'Login')
    expect(loginBtn).toBeTruthy()

    await loginBtn.trigger('click')
    expect(push).toHaveBeenCalledWith('/login')
  })

  it('does not show login button for authenticated users', () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'student'

    const wrapper = mount(HomeView)

    const loginBtn = wrapper.findAll('button').find((button) => button.text() === 'Login')
    expect(loginBtn).toBeUndefined()
    expect(wrapper.find('select').exists()).toBe(true)
  })
})
