import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OptionSelector from '../../src/components/ui/OptionSelector.vue'

describe('OptionSelector.vue', () => {
  it('renders label and emits change', async () => {
    const wrapper = mount(OptionSelector, {
      props: { label: 'Biology 103', checked: false, name: 'class' }
    })

    expect(wrapper.text()).toContain('Biology 103')
    await wrapper.find('input').trigger('change')
    expect(wrapper.emitted('change')).toBeTruthy()
  })
})
