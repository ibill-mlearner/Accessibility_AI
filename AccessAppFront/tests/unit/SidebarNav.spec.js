import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import SidebarNav from '../../src/components/SidebarNav.vue'
import { useAppStore } from '../../src/stores/appStore'

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
})
