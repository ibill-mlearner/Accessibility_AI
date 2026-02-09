import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import FeatureOptionCard from '../../src/components/classes/FeatureOptionCard.vue'

describe('FeatureOptionCard.vue', () => {
  it('renders feature title and description', () => {
    const wrapper = mount(FeatureOptionCard, {
      props: {
        item: { id: 1, title: 'Note Taking assistance', description: 'Desc', enabled: true }
      }
    })

    expect(wrapper.text()).toContain('Note Taking assistance')
    expect(wrapper.text()).toContain('Desc')
  })
})
