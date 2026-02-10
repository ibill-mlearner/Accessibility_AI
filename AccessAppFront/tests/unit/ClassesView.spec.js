import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import ClassesView from '../../src/views/ClassesView.vue'
import { useAppStore } from '../../src/stores/appStore'

describe('ClassesView.vue', () => {
  it('renders classes for the route role prop', async () => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.classes = [
      { id: 1, role: 'student', name: 'Biology 103', description: 'Student class' },
      { id: 2, role: 'instructor', name: 'Chemistry 213', description: 'Instructor class' }
    ]

    const wrapper = mount(ClassesView, {
      props: { role: 'student' }
    })

    expect(store.role).toBe('student')
    expect(wrapper.text()).toContain('Biology 103')
    expect(wrapper.text()).toContain('Instructor/contact')

    await wrapper.setProps({ role: 'instructor' })
    expect(wrapper.text()).toContain('Chemistry 213')
    expect(wrapper.text()).toContain('Class instructions')
  })
})
