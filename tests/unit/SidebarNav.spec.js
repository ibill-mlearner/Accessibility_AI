import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import SidebarNav from '../../src/components/SidebarNav.vue'
import { useAppStore } from '../../src/stores/appStore'

describe('SidebarNav.vue', () => {
  it('renders logo and chat list with active chat', () => {
    setActivePinia(createPinia())
    const store = useAppStore()
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
  })
})
