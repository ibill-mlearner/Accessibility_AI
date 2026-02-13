import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import HeaderBar from '../../src/components/HeaderBar.vue'
import { useAppStore } from '../../src/stores/appStore'

describe('HeaderBar.vue', () => {
  it('reserves space but hides header until model, active chat, and class are all selected', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.chats = [{ id: 10, title: 'Chat A' }]
    store.classes = [{ id: 20, role: 'student', name: 'Biology 103' }]

    const wrapper = mount(HeaderBar)

    expect(wrapper.find('header').classes()).toContain('header-bar--invisible')

    store.selectedModel = 'Llama 3.1 8B (local)'
    await wrapper.vm.$nextTick()
    expect(wrapper.find('header').classes()).toContain('header-bar--invisible')

    store.selectedChatId = 10
    await wrapper.vm.$nextTick()
    expect(wrapper.find('header').classes()).toContain('header-bar--invisible')

    store.selectedClassId = 20
    await wrapper.vm.$nextTick()
    expect(wrapper.find('header').classes()).not.toContain('header-bar--invisible')
    expect(wrapper.text()).toContain('Local Model: Llama 3.1 8B (local)')
    expect(wrapper.text()).toContain('Class: Biology 103')
  })
})
