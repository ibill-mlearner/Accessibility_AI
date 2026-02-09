import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import SavedNotesView from '../../src/views/SavedNotesView.vue'
import { useAppStore } from '../../src/stores/appStore'

describe('SavedNotesView.vue', () => {
  it('renders saved notes entries with action buttons', () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.notes = [
      { id: 1, class: 'Bio', date: '2026-02-09', chat: 'Chat 1', content: "System's response . . ." },
      { id: 2, class: 'Chem', date: '2026-02-09', chat: 'Chat 2', content: "User's prompt . . ." }
    ]

    const wrapper = mount(SavedNotesView)

    expect(wrapper.findAll('.saved-note')).toHaveLength(2)
    expect(wrapper.text()).toContain('Saved for class: Bio')
    expect(wrapper.findAll('button.btn')).toHaveLength(4)
  })
})
