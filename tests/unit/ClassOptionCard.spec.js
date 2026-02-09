import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ClassOptionCard from '../../src/components/classes/ClassOptionCard.vue'

describe('ClassOptionCard.vue', () => {
  it('renders class data and emits select event', async () => {
    const wrapper = mount(ClassOptionCard, {
      props: {
        item: { id: 1, name: 'Biology 103', description: 'Class desc' },
        checked: true,
        actionLabel: 'Instructor/contact'
      }
    })

    expect(wrapper.text()).toContain('Biology 103')
    expect(wrapper.text()).toContain('Instructor/contact')

    await wrapper.find('input').trigger('change')
    expect(wrapper.emitted('select')[0]).toEqual([1])
  })
})
