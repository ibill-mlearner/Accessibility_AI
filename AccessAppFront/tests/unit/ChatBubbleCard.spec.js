import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatBubbleCard from '../../src/components/chat/ChatBubbleCard.vue'

describe('ChatBubbleCard.vue', () => {
  it('renders text and optional action buttons', () => {
    const wrapper = mount(ChatBubbleCard, {
      props: { text: 'System message', showActions: true }
    })

    expect(wrapper.text()).toContain('System message')
    expect(wrapper.findAll('button.btn')).toHaveLength(2)
  })
})
