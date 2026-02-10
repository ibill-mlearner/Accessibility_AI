import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import HeaderBar from '../../src/components/HeaderBar.vue'
import { useAppStore } from '../../src/stores/appStore'

describe('HeaderBar.vue', () => {
  it('shows guest and authenticated header states', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    const wrapper = mount(HeaderBar)

    expect(wrapper.text()).toContain('Not logged in, current chat does not save')

    store.role = 'student'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Model Selected     Class selected')
  })
})
