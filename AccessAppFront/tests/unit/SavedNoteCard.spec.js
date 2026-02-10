import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SavedNoteCard from '../../src/components/notes/SavedNoteCard.vue'

describe('SavedNoteCard.vue', () => {
  it('renders note metadata and actions', () => {
    const wrapper = mount(SavedNoteCard, {
      props: {
        note: {
          id: 1,
          class: 'Bio',
          date: '2026-02-09',
          chat: 'Chat 1',
          content: 'System response'
        }
      }
    })

    expect(wrapper.text()).toContain('Saved for class: Bio')
    expect(wrapper.text()).toContain('System response')
    expect(wrapper.findAll('button.btn')).toHaveLength(2)
  })
})
