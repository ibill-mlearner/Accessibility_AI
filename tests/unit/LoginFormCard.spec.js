import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import LoginFormCard from '../../src/components/auth/LoginFormCard.vue'

describe('LoginFormCard.vue', () => {
  it('emits field updates and submit for valid input', async () => {
    const wrapper = mount(LoginFormCard, {
      props: {
        username: 'student',
        password: 'student123'
      }
    })

    const [userInput, passInput] = wrapper.findAll('input')
    await userInput.setValue('student-updated')
    await passInput.setValue('student1234')

    expect(wrapper.emitted('update:username')[0]).toEqual(['student-updated'])
    expect(wrapper.emitted('update:password')[0]).toEqual(['student1234'])

    await wrapper.find('button.icon-btn').trigger('click')
    expect(wrapper.emitted('submit')).toBeTruthy()
  })

  it('shows validation errors and does not emit submit when input is invalid', async () => {
    const wrapper = mount(LoginFormCard, {
      props: {
        username: '',
        password: '123'
      }
    })

    await wrapper.find('button.icon-btn').trigger('click')

    expect(wrapper.emitted('submit')).toBeFalsy()
    expect(wrapper.text()).toContain('Username is required.')
    expect(wrapper.text()).toContain('Password must be at least 6 characters.')
  })
})
