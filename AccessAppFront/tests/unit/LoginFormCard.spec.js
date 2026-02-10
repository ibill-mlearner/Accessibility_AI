import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import LoginFormCard from '../../src/components/auth/LoginFormCard.vue'

describe('LoginFormCard.vue', () => {
  it('emits field updates and submit', async () => {
    const wrapper = mount(LoginFormCard)

    const [userInput, passInput] = wrapper.findAll('input')
    await userInput.setValue('demo')
    await passInput.setValue('secret')

    expect(wrapper.emitted('update:username')[0]).toEqual(['demo'])
    expect(wrapper.emitted('update:password')[0]).toEqual(['secret'])

    await wrapper.find('button.icon-btn').trigger('click')
    expect(wrapper.emitted('submit')).toBeTruthy()
  })
})
