import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SidebarNav from '../../src/components/SidebarNav.vue'
import { useAuthStore } from '../../src/stores/authStore'
import { useChatStore } from '../../src/stores/chatStore'

const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const mod = await importOriginal()
  return { ...mod, useRouter: () => ({ push }) }
})

describe('SidebarNav.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts a new chat and routes home', async () => {
    const auth = useAuthStore()
    const chats = useChatStore()
    auth.isAuthenticated = true
    auth.role = 'student'
    chats.prepareNewChat = vi.fn()

    const wrapper = mount(SidebarNav, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } }
      }
    })

    await wrapper.get('button.btn.btn-outline-primary').trigger('click')
    expect(chats.prepareNewChat).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith('/')
  })

  it('maps chat list actions to store update/delete methods', async () => {
    const auth = useAuthStore()
    const chats = useChatStore()
    auth.isAuthenticated = true
    auth.role = 'student'
    chats.chats = [{ id: 5, title: 'My Chat' }]
    chats.selectedChatId = 5
    chats.deleteChat = vi.fn().mockResolvedValue()
    chats.updateChat = vi.fn().mockResolvedValue()

    const ChatListItemStub = {
      props: ['chat'],
      emits: ['archive', 'edit-title'],
      template: '<li><button class="emit-archive" @click="$emit(`archive`, chat.id)" /><button class="emit-edit" @click="$emit(`edit-title`, { chatId: chat.id, title: `Renamed` })" /></li>'
    }

    const wrapper = mount(SidebarNav, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          ChatListItem: ChatListItemStub
        }
      }
    })

    await wrapper.get('button.emit-archive').trigger('click')
    await wrapper.get('button.emit-edit').trigger('click')

    expect(chats.deleteChat).toHaveBeenCalledWith(5)
    expect(chats.updateChat).toHaveBeenCalledWith(5, { title: 'Renamed' })
  })
})
