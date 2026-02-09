import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OptionCard from '../../src/components/ui/OptionCard.vue'

describe('OptionCard.vue', () => {
  it('renders description and slots', () => {
    const wrapper = mount(OptionCard, {
      props: { description: 'card description' },
      slots: {
        selector: '<div class="selector-slot">selector</div>',
        action: '<button class="action-slot">action</button>'
      }
    })

    expect(wrapper.text()).toContain('card description')
    expect(wrapper.find('.selector-slot').exists()).toBe(true)
    expect(wrapper.find('.action-slot').exists()).toBe(true)
  })
})
