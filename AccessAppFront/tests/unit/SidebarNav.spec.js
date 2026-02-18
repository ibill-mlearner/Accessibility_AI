import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import SidebarNav from '../../src/components/SidebarNav.vue'
import { useAppStore } from '../../src/stores/appStore'

const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    useRouter: () => ({ push })
  }
})

describe('SidebarNav.vue', () => {
  it('renders chat list for authenticated users and allows selecting a chat', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'student'
    store.chats = [
      { id: 1, title: 'Chat 1' },
      { id: 2, title: 'Chat 2' }
    ]
    store.selectedChatId = 2

    const wrapper = mount(SidebarNav)

    expect(wrapper.text()).toContain('AI Project or Logo')
    expect(wrapper.text()).toContain('Chat 1')
    expect(wrapper.findAll('li.active')).toHaveLength(1)
    expect(wrapper.find('li.active').text()).toContain('Chat 2')

    await wrapper.findAll('button.chat-item')[0].trigger('click')
    expect(store.selectedChatId).toBe(1)
  })

  it('does not render chats for guest users', () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'guest'
    store.chats = [{ id: 1, title: 'Chat 1' }]

    const wrapper = mount(SidebarNav)

    expect(wrapper.find('.chat-list').exists()).toBe(false)
  })


  it('renders account actions for logged-in users and routes to profile/home on logout', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'student'
    store.isAuthenticated = true
    push.mockClear()

    const wrapper = mount(SidebarNav)
    const profileBtn = wrapper.findAll('button').find((button) => button.text() === 'Profile')
    const logoutBtn = wrapper.findAll('button').find((button) => button.text() === 'Logout')

    expect(profileBtn).toBeTruthy()
    expect(logoutBtn).toBeTruthy()

    await profileBtn.trigger('click')
    await logoutBtn.trigger('click')

    expect(push).toHaveBeenNthCalledWith(1, '/profile')
    expect(push).toHaveBeenNthCalledWith(2, '/')
    expect(store.role).toBe('guest')
    expect(store.isAuthenticated).toBe(false)
  })

  it('hides account actions when user is not logged in', () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.role = 'student'
    store.isAuthenticated = false

    const wrapper = mount(SidebarNav)

    expect(wrapper.findAll('button').some((button) => button.text() === 'Profile')).toBe(false)
    expect(wrapper.findAll('button').some((button) => button.text() === 'Logout')).toBe(false)
  })

})
