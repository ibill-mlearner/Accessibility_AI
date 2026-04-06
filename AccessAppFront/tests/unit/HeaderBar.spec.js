import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import HeaderBar from '../../src/components/HeaderBar.vue'
import { useAuthStore } from '../../src/stores/authStore'
import { useChatStore } from '../../src/stores/chatStore'
import { useClassStore } from '../../src/stores/classStore'

describe('HeaderBar.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('stays visible for authenticated users with a selected class, even without an active chat', () => {
    const auth = useAuthStore()
    const classes = useClassStore()
    const chats = useChatStore()

    auth.isAuthenticated = true
    auth.role = 'student'
    classes.classes = [{ id: 7, name: 'Biology 101' }]
    classes.selectedClassId = 7
    chats.selectedChatId = null
    chats.chats = []

    const wrapper = mount(HeaderBar)
    const header = wrapper.get('header')

    expect(header.classes()).not.toContain('header-bar--invisible')
    expect(header.attributes('aria-hidden')).toBe('false')
    expect(header.text()).toContain('Class: Biology 101')
  })

  it('hides for guest users', () => {
    const auth = useAuthStore()
    const classes = useClassStore()

    auth.isAuthenticated = false
    auth.role = 'guest'
    classes.classes = [{ id: 9, name: 'History' }]
    classes.selectedClassId = 9

    const wrapper = mount(HeaderBar)
    const header = wrapper.get('header')

    expect(header.classes()).toContain('header-bar--invisible')
    expect(header.attributes('aria-hidden')).toBe('true')
  })
})
