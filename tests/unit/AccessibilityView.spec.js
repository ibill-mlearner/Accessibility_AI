import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import AccessibilityView from '../../src/views/AccessibilityView.vue'
import { useAppStore } from '../../src/stores/appStore'

describe('AccessibilityView.vue', () => {
  it('renders feature cards from store', () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.features = [
      { id: 1, title: 'Feature A', description: 'Desc A', enabled: true },
      { id: 2, title: 'Feature B', description: 'Desc B', enabled: false }
    ]

    const wrapper = mount(AccessibilityView)
    expect(wrapper.text()).toContain('Feature A')
    expect(wrapper.text()).toContain('Desc B')
    expect(wrapper.findAll('.card-row')).toHaveLength(2)
  })
})
