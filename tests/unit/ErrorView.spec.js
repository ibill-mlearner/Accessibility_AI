import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ErrorView from '../../src/views/ErrorView.vue'

describe('ErrorView.vue', () => {
  it('renders error messaging', () => {
    const wrapper = mount(ErrorView)
    expect(wrapper.text()).toContain('AI Project or Logo')
    expect(wrapper.text()).toContain('40X: Page error please refer to the project owner')
  })
})
